import logging
import os
import re
import shutil
import subprocess
import tempfile
import time
import uuid
from pathlib import Path

import httpx
from pydantic import BaseModel, Field, ValidationError, model_validator
from sqlalchemy import select

from .db import SessionLocal
from .models import Embedding, Entity, ProcessingJob, Streamer, Transcript, TranscriptSegment, Video, VideoAsset, WikiEntry, WikiEntryEntity, WikiEntrySource, WikiEntryTopic, WikiRelationship, Topic

logger = logging.getLogger("afterlife.processing")
SEGMENT_SECONDS = 600


class ExtractedEntry(BaseModel):
    title: str = Field(min_length=4, max_length=180)
    summary: str = Field(min_length=12, max_length=500)
    body: str = Field(min_length=12, max_length=5000)
    category: str = Field(min_length=2, max_length=40)
    topics: list[str] = Field(max_length=8)
    entities: list[str] = Field(max_length=8)
    related_titles: list[str] = Field(max_length=8)
    start_seconds: int = Field(ge=0)
    end_seconds: int = Field(gt=0)
    confidence: float = Field(ge=0, le=1)

    @model_validator(mode="after")
    def check_range(self):
        if self.end_seconds <= self.start_seconds:
            raise ValueError("end_seconds must be after start_seconds")
        return self


class ExtractedBatch(BaseModel):
    entries: list[ExtractedEntry] = Field(max_length=20)


def _request(client: httpx.Client, url: str, **kwargs) -> httpx.Response:
    last_error: Exception | None = None
    for attempt in range(3):
        try:
            response = client.post(url, **kwargs)
            if response.status_code >= 500:
                response.raise_for_status()
            response.raise_for_status()
            return response
        except (httpx.TimeoutException, httpx.NetworkError, httpx.HTTPStatusError) as exc:
            last_error = exc
            if isinstance(exc, httpx.HTTPStatusError) and exc.response.status_code < 500 and exc.response.status_code not in (408, 429):
                raise
            if attempt < 2:
                time.sleep(2 ** attempt)
    raise RuntimeError("AI provider request failed after retries") from last_error


def _extract_entries(client: httpx.Client, api_key: str, model: str, transcript: str, duration: int) -> list[ExtractedEntry]:
    schema = ExtractedBatch.model_json_schema()
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": "Extract only notable events, recurring jokes, useful knowledge, people, or community milestones supported by this transcript. Return no entry if the transcript supports none. Timestamps must be seconds relative to this transcript chunk, not the source stream. Never infer unseen facts."},
            {"role": "user", "content": f"Transcript chunk duration: {duration} seconds.\nTranscript:\n{transcript[:50000]}"},
        ],
        "response_format": {"type": "json_schema", "json_schema": {"name": "stream_knowledge", "strict": True, "schema": schema}},
        "temperature": 0.1,
    }
    response = _request(client, "https://api.openai.com/v1/chat/completions",
                        headers={"Authorization": f"Bearer {api_key}"}, json=payload)
    content = response.json()["choices"][0]["message"]["content"]
    return ExtractedBatch.model_validate_json(content).entries


def _create_embeddings(client: httpx.Client, api_key: str, model: str, entry: WikiEntry) -> list[float] | None:
    try:
        response = _request(client, "https://api.openai.com/v1/embeddings", headers={"Authorization": f"Bearer {api_key}"},
                            json={"model": model, "input": f"{entry.title}\n{entry.summary}\n{entry.body}"})
        return response.json()["data"][0]["embedding"]
    except Exception:
        logger.exception("Embedding generation failed for wiki entry %s; the source-backed draft remains available", entry.id)
        return None


def get_ffmpeg_binary() -> str | None:
    path = shutil.which("ffmpeg")
    if path:
        return path
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        return None


def process_authorized_video(video_id: str, job_id: str) -> None:
    """Run a queued creator-authorized local upload; only mark indexed after source-linked drafts persist."""
    api_key = os.getenv("OPENAI_API_KEY")
    ffmpeg = get_ffmpeg_binary()
    if not api_key or not ffmpeg:
        _fail_job(job_id, video_id, "Processing unavailable: configure OPENAI_API_KEY and install FFmpeg.")
        return
    upload_dir = Path(os.getenv("UPLOAD_DIR", "./uploads")).resolve()
    with SessionLocal() as db:
        job = db.get(ProcessingJob, job_id)
        video = db.get(Video, video_id)
        if not job or not video:
            return
        asset = db.scalar(select(VideoAsset).where(VideoAsset.video_id == video_id))
        if not asset:
            _fail_job(job_id, video_id, "Creator-authorized media asset is missing.")
            return
        media_path = Path(asset.storage_key)
        if not media_path.is_file() or upload_dir not in media_path.parents:
            _fail_job(job_id, video_id, "Stored media path failed validation.")
            return
        streamer = db.get(Streamer, video.streamer_id)
        if not streamer:
            _fail_job(job_id, video_id, "Streamer record is missing.")
            return
        job.status = "running"
        job.attempts += 1
        video.status = "processing"
        db.commit()
        streamer_id, streamer_username = streamer.id, streamer.username

    transcript_rows: list[tuple[int, int, str]] = []
    pending_entries: list[tuple[ExtractedEntry, int]] = []
    try:
        with tempfile.TemporaryDirectory(prefix="afterlife-audio-", dir=upload_dir) as temp_dir:
            output_pattern = str(Path(temp_dir) / "audio-%03d.mp3")
            command = [ffmpeg, "-nostdin", "-hide_banner", "-loglevel", "error", "-i", str(media_path), "-vn",
                       "-ac", "1", "-ar", "16000", "-c:a", "libmp3lame", "-b:a", "64k", "-f", "segment",
                       "-segment_time", str(SEGMENT_SECONDS), "-reset_timestamps", "1", output_pattern]
            result = subprocess.run(command, capture_output=True, text=True, timeout=6 * 60 * 60, check=False)
            if result.returncode:
                raise RuntimeError("FFmpeg audio extraction failed: " + result.stderr[-1200:])
            audio_parts = sorted(Path(temp_dir).glob("audio-*.mp3"))
            if not audio_parts:
                raise RuntimeError("FFmpeg produced no audio segments")
            openai_model = os.getenv("OPENAI_MODEL", "gpt-4.1-mini")
            embedding_model = os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small")
            with httpx.Client(timeout=httpx.Timeout(120, connect=20)) as client:
                for index, audio_path in enumerate(audio_parts):
                    offset = index * SEGMENT_SECONDS
                    with audio_path.open("rb") as audio_file:
                        response = _request(client, "https://api.openai.com/v1/audio/transcriptions",
                                            headers={"Authorization": f"Bearer {api_key}"},
                                            data={"model": "whisper-1", "response_format": "verbose_json",
                                                  "timestamp_granularities[]": "segment"},
                                            files={"file": (audio_path.name, audio_file, "audio/mpeg")})
                    transcript_data = response.json()
                    local_segments = transcript_data.get("segments", [])
                    chunk_text = transcript_data.get("text", "")
                    if not local_segments and chunk_text.strip():
                        local_segments = [{"start": 0, "end": SEGMENT_SECONDS, "text": chunk_text}]
                    for segment in local_segments:
                        start, end = int(segment.get("start", 0)) + offset, int(segment.get("end", 0)) + offset
                        text = str(segment.get("text", "")).strip()
                        if text and end > start:
                            transcript_rows.append((start, end, text))
                    chunk_duration = max(1, min(SEGMENT_SECONDS, int(max((float(s.get("end", 0)) for s in local_segments), default=SEGMENT_SECONDS))))
                    if chunk_text.strip():
                        try:
                            drafts = _extract_entries(client, api_key, openai_model, chunk_text, chunk_duration)
                        except (ValidationError, KeyError, ValueError) as exc:
                            logger.exception("Structured extraction response was invalid for video %s", video_id)
                            raise RuntimeError("Knowledge extraction returned invalid structured output") from exc
                        for draft in drafts:
                            if draft.end_seconds > chunk_duration:
                                logger.warning("Dropping out-of-range model timestamp from video %s", video_id)
                                continue
                            pending_entries.append((draft, offset))

                with SessionLocal() as db:
                    video = db.get(Video, video_id)
                    job = db.get(ProcessingJob, job_id)
                    if not video or not job:
                        return
                    transcript = db.scalar(select(Transcript).where(Transcript.video_id == video_id))
                    if transcript is None:
                        transcript = Transcript(video_id=video_id, language="en", provider="openai:whisper-1", status="complete")
                        db.add(transcript)
                        db.flush()
                    else:
                        transcript.status = "complete"
                        db.query(TranscriptSegment).filter(TranscriptSegment.transcript_id == transcript.id).delete()
                    db.add_all([TranscriptSegment(transcript_id=transcript.id, start_seconds=start, end_seconds=end, text=text)
                                for start, end, text in transcript_rows])
                    existing_titles: dict[str, WikiEntry] = {}
                    for draft, offset in pending_entries:
                        slug_base = re.sub(r"[^a-z0-9]+", "-", draft.title.lower()).strip("-")[:100] or "moment"
                        slug = f"{streamer_username}-{slug_base}-{offset}-{uuid.uuid4().hex[:6]}"
                        entry = WikiEntry(streamer_id=streamer_id, slug=slug, title=draft.title, summary=draft.summary,
                                          body=draft.body, category=draft.category, status="pending_review",
                                          confidence=draft.confidence, is_sample=False)
                        db.add(entry)
                        db.flush()
                        source_start, source_end = offset + draft.start_seconds, offset + draft.end_seconds
                        db.add(WikiEntrySource(wiki_entry_id=entry.id, video_id=video_id, start_seconds=source_start,
                                               end_seconds=source_end, citation_note="Creator-authorized upload · AI draft pending review"))
                        existing_titles[draft.title.casefold()] = entry
                        for topic_name in draft.topics:
                            topic = db.scalar(select(Topic).where(Topic.streamer_id == streamer_id, Topic.name == topic_name))
                            if topic is None:
                                topic = Topic(streamer_id=streamer_id, name=topic_name)
                                db.add(topic)
                                db.flush()
                            db.add(WikiEntryTopic(wiki_entry_id=entry.id, topic_id=topic.id))
                        for entity_name in draft.entities:
                            entity = db.scalar(select(Entity).where(Entity.streamer_id == streamer_id, Entity.name == entity_name))
                            if entity is None:
                                entity = Entity(streamer_id=streamer_id, name=entity_name, kind="unclassified")
                                db.add(entity)
                                db.flush()
                            db.add(WikiEntryEntity(wiki_entry_id=entry.id, entity_id=entity.id))
                        vector = _create_embeddings(client, api_key, embedding_model, entry)
                        if vector:
                            db.add(Embedding(owner_type="wiki_entry", owner_id=entry.id, model=embedding_model, vector_json=vector))
                    db.flush()
                    for draft, _offset in pending_entries:
                        source_entry = existing_titles.get(draft.title.casefold())
                        if not source_entry:
                            continue
                        for related_title in draft.related_titles:
                            target = existing_titles.get(related_title.casefold())
                            if target and target.id != source_entry.id:
                                db.add(WikiRelationship(source_entry_id=source_entry.id, target_entry_id=target.id, kind="related"))
                    job.status = "complete"
                    job.error = None
                    video.status = "indexed"
                    db.commit()
                    logger.info("Indexed creator-authorized video %s: %d transcript segments, %d review drafts",
                                video_id, len(transcript_rows), len(pending_entries))
    except Exception as exc:
        logger.exception("Media processing failed for video %s", video_id)
        _fail_job(job_id, video_id, str(exc)[:2000])


def _fail_job(job_id: str, video_id: str, error: str) -> None:
    with SessionLocal() as db:
        job = db.get(ProcessingJob, job_id)
        video = db.get(Video, video_id)
        if job:
            job.status = "failed"
            job.error = error
        if video:
            video.status = "processing_failed"
        db.commit()
