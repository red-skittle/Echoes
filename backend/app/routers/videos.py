import os
import uuid
import shutil
from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, BackgroundTasks
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import Video, Streamer, Transcript, TranscriptSegment, WikiEntrySource, ProcessingJob, VideoAsset
from app.schemas import VideoResponse, TranscriptResponse, WikiSourceSchema, ProcessingJobResponse
from app.services.ai_pipeline import process_video_pipeline

router = APIRouter(prefix="/api/videos", tags=["Videos"])

UPLOAD_DIR = os.path.join(os.getcwd(), "media_uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

@router.get("", response_model=List[VideoResponse])
def list_videos(
    streamer_username: Optional[str] = None,
    indexed_only: Optional[bool] = False,
    db: Session = Depends(get_db)
):
    query = db.query(Video)
    if streamer_username:
        streamer = db.query(Streamer).filter(Streamer.username.ilike(streamer_username)).first()
        if not streamer:
            return []
        query = query.filter(Video.streamer_id == streamer.id)
    if indexed_only:
        query = query.filter(Video.is_indexed == True)
    
    videos = query.order_by(Video.published_at.desc()).all()
    return [VideoResponse.model_validate(v) for v in videos]

@router.get("/{video_id}")
def get_video_detail(video_id: str, db: Session = Depends(get_db)):
    video = db.query(Video).filter(Video.id == video_id).first()
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")

    transcript = db.query(Transcript).filter(Transcript.video_id == video.id).first()
    sources = db.query(WikiEntrySource).filter(WikiEntrySource.video_id == video.id).all()
    jobs = db.query(ProcessingJob).filter(ProcessingJob.video_id == video.id).order_by(ProcessingJob.created_at.desc()).all()

    # Formatted moments/sources linked to this video
    moments = []
    for s in sources:
        moments.append({
            "id": s.id,
            "timestamp": s.start_timestamp,
            "end_timestamp": s.end_timestamp,
            "quote": s.quote_text,
            "note": s.context_note,
            "wiki_title": s.wiki_entry.title if s.wiki_entry else None,
            "wiki_slug": s.wiki_entry.slug if s.wiki_entry else None,
            "category": s.wiki_entry.category if s.wiki_entry else "Moment"
        })

    # Sort moments chronologically
    moments.sort(key=lambda x: x["timestamp"])

    return {
        "video": VideoResponse.model_validate(video),
        "streamer": {
            "id": video.streamer.id,
            "username": video.streamer.username,
            "display_name": video.streamer.display_name,
            "profile_image_url": video.streamer.profile_image_url
        },
        "transcript": TranscriptResponse.model_validate(transcript) if transcript else None,
        "moments": moments,
        "recent_job": ProcessingJobResponse.model_validate(jobs[0]) if jobs else None
    }

@router.post("/import")
def import_twitch_metadata(
    twitch_video_id: str = Form(...),
    streamer_id: str = Form(...),
    title: str = Form(...),
    duration_seconds: int = Form(0),
    thumbnail_url: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    db: Session = Depends(get_db)
):
    """Imports Twitch metadata without faking indexing."""
    existing = db.query(Video).filter(Video.twitch_video_id == twitch_video_id).first()
    if existing:
        return {"message": "Video metadata already imported", "video": VideoResponse.model_validate(existing)}

    video = Video(
        id=str(uuid.uuid4()),
        streamer_id=streamer_id,
        twitch_video_id=twitch_video_id,
        title=title,
        description=description,
        published_at=datetime.utcnow(),
        duration_seconds=duration_seconds,
        thumbnail_url=thumbnail_url or "https://images.unsplash.com/photo-1542751371-adc38448a05e?w=640",
        view_count=0,
        is_indexed=False,
        processing_status="unprocessed"
    )
    db.add(video)
    db.commit()
    db.refresh(video)
    return {"message": "Metadata imported successfully. Ready for media upload or indexing.", "video": VideoResponse.model_validate(video)}

@router.post("/upload")
async def upload_media_asset(
    video_id: str = Form(...),
    file: UploadFile = File(...),
    background_tasks: BackgroundTasks = None,
    db: Session = Depends(get_db)
):
    """Uploads creator-authorized media file for transcription & AI wiki extraction."""
    video = db.query(Video).filter(Video.id == video_id).first()
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")

    ext = os.path.splitext(file.filename)[1]
    safe_filename = f"{video.id}_{int(datetime.utcnow().timestamp())}{ext}"
    file_path = os.path.join(UPLOAD_DIR, safe_filename)

    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    file_size = os.path.getsize(file_path)

    asset = VideoAsset(
        id=str(uuid.uuid4()),
        video_id=video.id,
        asset_type="raw_video",
        file_path=file_path,
        mime_type=file.content_type,
        file_size_bytes=file_size,
        duration_seconds=float(video.duration_seconds)
    )
    db.add(asset)

    # Create job
    job = ProcessingJob(
        id=str(uuid.uuid4()),
        video_id=video.id,
        job_type="ingestion",
        status="queued",
        progress=0,
        current_step="Uploaded media received. Waiting to start pipeline."
    )
    db.add(job)
    video.processing_status = "pending"
    db.commit()

    return {
        "status": "uploaded",
        "asset_id": asset.id,
        "job_id": job.id,
        "file_name": safe_filename,
        "size_bytes": file_size
    }

@router.post("/{video_id}/process")
def trigger_video_processing(
    video_id: str,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """Starts the AI processing pipeline (Audio -> Transcription -> Topic -> Wiki -> Entity -> Embeddings)."""
    video = db.query(Video).filter(Video.id == video_id).first()
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")

    job = ProcessingJob(
        id=str(uuid.uuid4()),
        video_id=video.id,
        job_type="wiki_extraction",
        status="in_progress",
        progress=5,
        current_step="Starting AI extraction pipeline..."
    )
    db.add(job)
    video.processing_status = "processing"
    db.commit()

    # Trigger background pipeline
    background_tasks.add_task(process_video_pipeline, video.id, job.id)

    return {
        "message": "AI Processing Pipeline launched",
        "job_id": job.id,
        "video_id": video.id,
        "status": "in_progress"
    }

