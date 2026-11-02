import hmac
import hashlib
import logging
import math
import os
import re
import secrets
import shutil
import uuid
from datetime import datetime
from pathlib import Path
from urllib.parse import urlencode
from contextlib import asynccontextmanager
from typing import Literal

import httpx
from dotenv import load_dotenv
from fastapi import BackgroundTasks, Depends, FastAPI, File, Form, Header, HTTPException, Query, Request, Response, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from sqlalchemy import bindparam, func, select, text
from sqlalchemy.orm import Session
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer
from starlette.responses import RedirectResponse

load_dotenv()

from .db import Base, SessionLocal, engine, get_db
from .models import Contribution, Embedding, ProcessingJob, Streamer, StreamerMembership, User, Video, VideoAsset, WikiEntry, WikiEntrySource
from .seed import seed_demo

REVIEW_TOKEN = os.getenv("AFTERLIFE_REVIEW_TOKEN", "")
PUBLIC_ENTRY_STATUSES = ("verified", "approved", "sample")
logger = logging.getLogger("afterlife.api")
SESSION_COOKIE = "afterlife_session"
SESSION_SECRET = os.getenv("SESSION_SECRET", "development-only-change-this-session-secret")
session_signer = URLSafeTimedSerializer(SESSION_SECRET, salt="afterlife-session-v1")


@asynccontextmanager
async def lifespan(_: FastAPI):
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        seed_demo(db)
    yield


app = FastAPI(title="Afterlife API", version="0.2.0", description="Video-first community encyclopedia API", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[os.getenv("WEB_ORIGIN", "http://localhost:3000")],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "OPTIONS"],
    allow_headers=["Content-Type", "X-Review-Token"],
)


class ContributionCreate(BaseModel):
    streamer_username: str = "mossybytes"
    wiki_entry_id: str | None = None
    contributor_name: str = Field(min_length=2, max_length=100)
    kind: Literal["suggestion", "correction", "timestamp"] = "suggestion"
    title: str = Field(min_length=4, max_length=240)
    body: str = Field(min_length=10, max_length=5000)


class ContributionReview(BaseModel):
    status: Literal["approved", "rejected"]
    review_note: str | None = Field(default=None, max_length=1000)


class WikiDraftReview(BaseModel):
    status: Literal["verified", "rejected"]


class SearchRequest(BaseModel):
    query: str = Field(min_length=3, max_length=500)
    streamer_username: str = "mossybytes"
    limit: int = Field(default=8, ge=1, le=20)


class VideoImportRequest(BaseModel):
    streamer_username: str = Field(min_length=1, max_length=100, pattern=r"^[A-Za-z0-9_]+$")


def streamer_or_404(db: Session, username: str) -> Streamer:
    item = db.scalar(select(Streamer).where(func.lower(Streamer.username) == username.lower()))
    if item is None:
        raise HTTPException(404, "Streamer wiki not found")
    return item


def video_summary(video: Video) -> dict:
    return {"id": video.id, "title": video.title, "url": video.url, "twitch_video_id": video.twitch_video_id, "thumbnail_url": video.thumbnail_url,
            "published_at": video.published_at, "duration_seconds": video.duration_seconds,
            "status": video.status, "is_sample": video.is_sample}


def entry_summary(db: Session, entry: WikiEntry) -> dict:
    source = db.scalar(select(WikiEntrySource).where(WikiEntrySource.wiki_entry_id == entry.id).order_by(WikiEntrySource.start_seconds))
    video = db.get(Video, source.video_id) if source else None
    return {"id": entry.id, "slug": entry.slug, "title": entry.title, "summary": entry.summary,
            "category": entry.category, "status": entry.status, "is_sample": entry.is_sample,
            "source": ({"start_seconds": source.start_seconds, "end_seconds": source.end_seconds,
                        "video": video_summary(video)} if source and video else None)}


def require_reviewer(token: str | None) -> None:
    if not REVIEW_TOKEN:
        raise HTTPException(503, "Wiki review is disabled until AFTERLIFE_REVIEW_TOKEN is configured")
    if token is None or not hmac.compare_digest(token, REVIEW_TOKEN):
        raise HTTPException(403, "Reviewer authorization required")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "afterlife-api"}


def session_user_id(request: Request) -> str | None:
    value = request.cookies.get(SESSION_COOKIE)
    if not value:
        return None
    try:
        return session_signer.loads(value, max_age=60 * 60 * 24 * 14).get("sub")
    except (BadSignature, SignatureExpired, AttributeError):
        return None


@app.get("/api/auth/status")
def auth_status(request: Request, db: Session = Depends(get_db)) -> dict:
    configured = bool(os.getenv("TWITCH_CLIENT_ID") and os.getenv("TWITCH_CLIENT_SECRET"))
    user_id = session_user_id(request)
    user = db.get(User, user_id) if user_id else None
    memberships = db.scalars(select(Streamer).join(StreamerMembership, StreamerMembership.streamer_id == Streamer.id)
                              .where(StreamerMembership.user_id == user_id, StreamerMembership.role.in_(["owner", "moderator"]))).all() if user else []
    return {"authenticated": user is not None, "display_name": user.display_name if user else None,
            "streamers": [{"id": s.id, "username": s.username} for s in memberships],
            "twitch_oauth_configured": configured}


@app.get("/api/auth/twitch")
def twitch_auth(request: Request) -> Response:
    client_id = (os.getenv("TWITCH_CLIENT_ID") or "").strip().lower()
    client_secret = (os.getenv("TWITCH_CLIENT_SECRET") or "").strip()
    callback = (os.getenv("TWITCH_REDIRECT_URI") or "").strip()
    if not client_id or not client_secret or not callback:
        raise HTTPException(503, "Twitch OAuth is not configured. Add Twitch application credentials to the backend environment.")
    state = secrets.token_urlsafe(32)
    params = {"client_id": client_id, "redirect_uri": callback, "response_type": "code", "scope": "user:read:email", "state": state}
    response = RedirectResponse("https://id.twitch.tv/oauth2/authorize?" + urlencode(params), status_code=302)
    response.set_cookie("afterlife_oauth_state", state, max_age=600, httponly=True, secure=request.url.scheme == "https", samesite="lax", path="/")
    return response


@app.get("/api/auth/twitch/callback")
async def twitch_callback(request: Request, code: str | None = None, state: str | None = None,
                          error: str | None = None, db: Session = Depends(get_db)) -> Response:
    if error:
        raise HTTPException(400, f"Twitch authorization was not completed: {error}")
    saved_state = request.cookies.get("afterlife_oauth_state")
    if not code or not state or not saved_state or not secrets.compare_digest(state, saved_state):
        raise HTTPException(400, "OAuth state validation failed. Start Twitch sign-in again.")
    client_id = (os.getenv("TWITCH_CLIENT_ID") or "").strip().lower()
    client_secret = (os.getenv("TWITCH_CLIENT_SECRET") or "").strip()
    if not client_id or not client_secret:
        raise HTTPException(503, "Twitch OAuth is not configured")
    callback = (os.getenv("TWITCH_REDIRECT_URI") or "").strip()
    if not callback:
        raise HTTPException(503, "Twitch OAuth redirect URI is not configured")
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            token_response = await client.post("https://id.twitch.tv/oauth2/token", data={
                "client_id": client_id, "client_secret": client_secret, "code": code,
                "grant_type": "authorization_code", "redirect_uri": callback,
            })
            token_response.raise_for_status()
            access_token = token_response.json()["access_token"]
            profile_response = await client.get("https://api.twitch.tv/helix/users", headers={
                "Client-Id": client_id, "Authorization": f"Bearer {access_token}",
            })
            profile_response.raise_for_status()
            profile_data = profile_response.json().get("data", [])
    except (httpx.HTTPError, KeyError, ValueError) as exc:
        raise HTTPException(502, "Twitch sign-in failed while validating the account") from exc
    if not profile_data:
        raise HTTPException(502, "Twitch did not return an account profile")
    profile = profile_data[0]
    user = db.scalar(select(User).where(User.twitch_id == profile["id"]))
    if user is None:
        user = User(twitch_id=profile["id"], display_name=profile.get("display_name") or profile["login"], avatar_url=profile.get("profile_image_url"))
        db.add(user)
        db.flush()
    else:
        user.display_name = profile.get("display_name") or profile["login"]
        user.avatar_url = profile.get("profile_image_url")
    streamer = db.scalar(select(Streamer).where(Streamer.twitch_id == profile["id"]))
    if streamer is None:
        streamer = db.scalar(select(Streamer).where(func.lower(Streamer.username) == profile["login"].lower()))
        if streamer is None:
            streamer = Streamer(twitch_id=profile["id"], username=profile["login"].lower(),
                                display_name=profile.get("display_name") or profile["login"],
                                description=profile.get("description") or "", avatar_url=profile.get("profile_image_url"))
            db.add(streamer)
            db.flush()
        elif streamer.is_sample:
            streamer = None
        elif streamer.twitch_id not in (None, profile["id"]):
            raise HTTPException(409, "This username is already linked to a different Twitch account")
        elif streamer is not None:
            streamer.twitch_id = profile["id"]
    if streamer and db.scalar(select(StreamerMembership.id).where(StreamerMembership.streamer_id == streamer.id,
                                                     StreamerMembership.user_id == user.id)) is None:
        db.add(StreamerMembership(streamer_id=streamer.id, user_id=user.id, role="owner"))
    db.commit()
    session = session_signer.dumps({"sub": user.id})
    frontend = os.getenv("WEB_APP_URL", "http://localhost:3000")
    response = RedirectResponse(frontend + "/dashboard", status_code=303)
    response.delete_cookie("afterlife_oauth_state", path="/")
    response.set_cookie(SESSION_COOKIE, session, max_age=60 * 60 * 24 * 14, httponly=True,
                        secure=request.url.scheme == "https", samesite="lax", path="/")
    return response


@app.get("/api/auth/me")
def auth_me(request: Request, db: Session = Depends(get_db)) -> dict:
    user_id = session_user_id(request)
    if not user_id:
        raise HTTPException(401, "Sign in with Twitch to access this account")
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(401, "Session account no longer exists")
    memberships = db.scalars(select(Streamer).join(StreamerMembership, StreamerMembership.streamer_id == Streamer.id)
                              .where(StreamerMembership.user_id == user.id, StreamerMembership.role.in_(["owner", "moderator"]))).all()
    return {"id": user.id, "display_name": user.display_name, "avatar_url": user.avatar_url,
            "streamers": [{"id": s.id, "username": s.username} for s in memberships]}


@app.post("/api/auth/logout")
def auth_logout() -> Response:
    response = Response(status_code=204)
    response.delete_cookie(SESSION_COOKIE, path="/")
    return response


@app.get("/api/streamers")
def list_streamers(query: str | None = Query(default=None, max_length=100), limit: int = Query(default=20, ge=1, le=100),
                   offset: int = Query(default=0, ge=0), db: Session = Depends(get_db)) -> dict:
    statement = select(Streamer)
    if query:
        statement = statement.where(Streamer.username.ilike(f"%{query}%") | Streamer.display_name.ilike(f"%{query}%"))
    total = db.scalar(select(func.count()).select_from(statement.subquery())) or 0
    streamers = db.scalars(statement.order_by(Streamer.created_at.desc()).offset(offset).limit(limit)).all()
    return {"items": [{"id": s.id, "username": s.username, "display_name": s.display_name,
                       "description": s.description, "avatar_url": s.avatar_url, "is_sample": s.is_sample,
                       "video_count": db.scalar(select(func.count(Video.id)).where(Video.streamer_id == s.id)) or 0,
                       "article_count": db.scalar(select(func.count(WikiEntry.id)).where(WikiEntry.streamer_id == s.id, WikiEntry.status.in_(PUBLIC_ENTRY_STATUSES))) or 0} for s in streamers],
            "total": total, "limit": limit, "offset": offset}


@app.get("/api/streamers/{username}")
def get_streamer(username: str, db: Session = Depends(get_db)) -> dict:
    s = streamer_or_404(db, username)
    entries = db.scalars(select(WikiEntry).where(WikiEntry.streamer_id == s.id, WikiEntry.status.in_(PUBLIC_ENTRY_STATUSES)).order_by(WikiEntry.created_at.desc()).limit(12)).all()
    videos = db.scalars(select(Video).where(Video.streamer_id == s.id).order_by(Video.published_at.desc()).limit(6)).all()
    return {"id": s.id, "username": s.username, "display_name": s.display_name, "description": s.description,
            "avatar_url": s.avatar_url, "is_sample": s.is_sample,
            "video_count": db.scalar(select(func.count(Video.id)).where(Video.streamer_id == s.id)) or 0,
            "article_count": db.scalar(select(func.count(WikiEntry.id)).where(WikiEntry.streamer_id == s.id, WikiEntry.status.in_(PUBLIC_ENTRY_STATUSES))) or 0,
            "entries": [entry_summary(db, e) for e in entries], "videos": [video_summary(v) for v in videos]}


@app.get("/api/streamers/{username}/wiki")
def get_streamer_wiki(username: str, category: str | None = None, db: Session = Depends(get_db)) -> dict:
    s = streamer_or_404(db, username)
    statement = select(WikiEntry).where(WikiEntry.streamer_id == s.id, WikiEntry.status.in_(PUBLIC_ENTRY_STATUSES))
    if category:
        statement = statement.where(WikiEntry.category.ilike(category))
    entries = db.scalars(statement.order_by(WikiEntry.title)).all()
    return {"streamer": s.username, "items": [entry_summary(db, e) for e in entries], "total": len(entries)}


@app.get("/api/wiki/{slug}")
def get_wiki_entry(slug: str, db: Session = Depends(get_db)) -> dict:
    entry = db.scalar(select(WikiEntry).where(WikiEntry.slug == slug, WikiEntry.status.in_(PUBLIC_ENTRY_STATUSES)))
    if entry is None:
        raise HTTPException(404, "Wiki entry not found")
    sources = db.scalars(select(WikiEntrySource).where(WikiEntrySource.wiki_entry_id == entry.id)).all()
    streamer = db.get(Streamer, entry.streamer_id)
    return {**entry_summary(db, entry), "body": entry.body, "confidence": entry.confidence,
            "streamer": streamer.username if streamer else None,
            "sources": [{"start_seconds": src.start_seconds, "end_seconds": src.end_seconds,
                         "citation_note": src.citation_note, "video": video_summary(db.get(Video, src.video_id))} for src in sources]}


@app.get("/api/dashboard/review")
def list_review_drafts(request: Request, db: Session = Depends(get_db)) -> dict:
    user_id = session_user_id(request)
    if not user_id:
        raise HTTPException(401, "Sign in to review your generated wiki drafts")
    streamer_ids = select(StreamerMembership.streamer_id).where(StreamerMembership.user_id == user_id,
                                                                  StreamerMembership.role == "owner")
    entries = db.scalars(select(WikiEntry).where(WikiEntry.streamer_id.in_(streamer_ids),
                                                  WikiEntry.status == "pending_review").order_by(WikiEntry.created_at.desc())).all()
    return {"items": [entry_summary(db, entry) for entry in entries], "total": len(entries)}


@app.patch("/api/wiki/{entry_id}/review")
def review_wiki_draft(entry_id: str, data: WikiDraftReview, request: Request, db: Session = Depends(get_db)) -> dict:
    entry = db.get(WikiEntry, entry_id)
    if entry is None:
        raise HTTPException(404, "Wiki draft not found")
    require_streamer_owner(db, session_user_id(request), entry.streamer_id)
    if entry.status != "pending_review":
        raise HTTPException(409, "Only pending AI drafts can be reviewed")
    entry.status = data.status
    db.commit()
    return {"id": entry.id, "slug": entry.slug, "status": entry.status}


@app.get("/api/videos")
def list_videos(streamer_username: str = "mossybytes", limit: int = Query(default=20, ge=1, le=100), db: Session = Depends(get_db)) -> dict:
    streamer = streamer_or_404(db, streamer_username)
    videos = db.scalars(select(Video).where(Video.streamer_id == streamer.id).order_by(Video.published_at.desc()).limit(limit)).all()
    return {"items": [video_summary(v) for v in videos], "total": len(videos)}


@app.post("/api/videos/import")
async def import_twitch_videos(data: VideoImportRequest, db: Session = Depends(get_db)) -> dict:
    client_id = (os.getenv("TWITCH_CLIENT_ID") or "").strip().lower()
    client_secret = (os.getenv("TWITCH_CLIENT_SECRET") or "").strip()
    if not client_id or not client_secret:
        raise HTTPException(503, "Twitch app credentials are required to import public video metadata")
    try:
        async with httpx.AsyncClient(timeout=20) as client:
            token_response = await client.post("https://id.twitch.tv/oauth2/token", data={
                "client_id": client_id, "client_secret": client_secret, "grant_type": "client_credentials"})
            token_response.raise_for_status()
            headers = {"Client-Id": client_id, "Authorization": f"Bearer {token_response.json()['access_token']}"}
            user_response = await client.get("https://api.twitch.tv/helix/users", headers=headers,
                                             params={"login": data.streamer_username.lower()})
            user_response.raise_for_status()
            users = user_response.json().get("data", [])
            if not users:
                raise HTTPException(404, "Twitch channel not found")
            profile = users[0]
            videos_response = await client.get("https://api.twitch.tv/helix/videos", headers=headers,
                                               params={"user_id": profile["id"], "type": "archive", "sort": "time", "first": 100})
            videos_response.raise_for_status()
            remote_videos = videos_response.json().get("data", [])
    except HTTPException:
        raise
    except (httpx.HTTPError, KeyError, ValueError) as exc:
        raise HTTPException(502, "Twitch metadata request failed") from exc
    streamer = db.scalar(select(Streamer).where(Streamer.twitch_id == profile["id"]))
    if streamer is None:
        streamer = db.scalar(select(Streamer).where(func.lower(Streamer.username) == profile["login"].lower()))
    if streamer is not None and streamer.is_sample:
        raise HTTPException(409, "This Twitch login matches the synthetic demo account name; demo content was left unchanged")
    if streamer is not None and streamer.twitch_id not in (None, profile["id"]):
        raise HTTPException(409, "This username is already linked to a different Twitch account")
    if streamer is None:
        streamer = Streamer(twitch_id=profile["id"], username=profile["login"].lower(),
                            display_name=profile.get("display_name") or profile["login"],
                            description=profile.get("description") or "", avatar_url=profile.get("profile_image_url"))
        db.add(streamer)
        db.flush()
    else:
        streamer.twitch_id = profile["id"]
        streamer.display_name = profile.get("display_name") or profile["login"]
        streamer.avatar_url = profile.get("profile_image_url")
        streamer.is_sample = False
    imported = 0
    for item in remote_videos:
        video = db.scalar(select(Video).where(Video.streamer_id == streamer.id, Video.twitch_video_id == item["id"]))
        published = datetime.fromisoformat(item["created_at"].replace("Z", "+00:00")) if item.get("created_at") else None
        duration = sum(int(amount) * {"h": 3600, "m": 60, "s": 1}[unit]
                       for amount, unit in re.findall(r"(\d+)([hms])", item.get("duration", "")))
        if video is None:
            video = Video(streamer_id=streamer.id, twitch_video_id=item["id"], title=item.get("title") or "Untitled Twitch video",
                          url=item.get("url"), thumbnail_url=item.get("thumbnail_url"), published_at=published,
                          duration_seconds=duration, status="metadata_only", is_sample=False)
            db.add(video)
            imported += 1
        else:
            video.title = item.get("title") or video.title
            video.url = item.get("url")
            video.thumbnail_url = item.get("thumbnail_url")
            video.published_at = published
            video.duration_seconds = duration
            video.status = "metadata_only"
            video.is_sample = False
    db.commit()
    return {"streamer": streamer.username, "imported": imported, "received": len(remote_videos),
            "message": "Imported Twitch metadata only. No video media was downloaded or indexed."}


def require_streamer_owner(db: Session, user_id: str | None, streamer_id: str) -> User:
    if not user_id:
        raise HTTPException(401, "Sign in with the Twitch account that owns this channel")
    user = db.get(User, user_id)
    membership = db.scalar(select(StreamerMembership).where(StreamerMembership.user_id == user_id,
                                                            StreamerMembership.streamer_id == streamer_id,
                                                            StreamerMembership.role == "owner"))
    if user is None or membership is None:
        raise HTTPException(403, "Only the channel owner can manage uploaded media")
    return user


@app.post("/api/videos/upload", status_code=201)
async def upload_authorized_video(
    request: Request,
    streamer_username: str = Form(..., min_length=1, max_length=100),
    title: str = Form(..., min_length=3, max_length=300),
    media: UploadFile = File(...),
    db: Session = Depends(get_db),
) -> dict:
    streamer = streamer_or_404(db, streamer_username)
    user = require_streamer_owner(db, session_user_id(request), streamer.id)
    allowed_extensions = {".mp4", ".mov", ".mkv", ".webm", ".m4v", ".mp3", ".wav", ".m4a"}
    extension = Path(media.filename or "").suffix.lower()
    if extension not in allowed_extensions:
        raise HTTPException(415, "Upload an MP4, MOV, MKV, WebM, M4V, MP3, WAV, or M4A file")
    max_bytes = max(1, int(os.getenv("MAX_UPLOAD_SIZE_MB", "2048"))) * 1024 * 1024
    upload_dir = Path(os.getenv("UPLOAD_DIR", "./uploads")).resolve()
    upload_dir.mkdir(parents=True, exist_ok=True)
    media_path = upload_dir / f"{uuid.uuid4().hex}{extension}"
    checksum = hashlib.sha256()
    total = 0
    try:
        with media_path.open("xb") as destination:
            while chunk := await media.read(1024 * 1024):
                total += len(chunk)
                if total > max_bytes:
                    raise HTTPException(413, f"Upload exceeds the {max_bytes // (1024 * 1024)} MB limit")
                checksum.update(chunk)
                destination.write(chunk)
    except Exception:
        media_path.unlink(missing_ok=True)
        raise
    finally:
        await media.close()
    digest = checksum.hexdigest()
    duplicate = db.scalar(select(VideoAsset).where(VideoAsset.checksum_sha256 == digest))
    if duplicate:
        media_path.unlink(missing_ok=True)
        raise HTTPException(409, "This exact media file has already been uploaded")
    video = Video(streamer_id=streamer.id, title=title.strip(), status="uploaded", is_sample=False)
    db.add(video)
    db.flush()
    db.add(VideoAsset(video_id=video.id, storage_key=str(media_path), checksum_sha256=digest,
                      authorized_by_user_id=user.id, content_type=media.content_type or "application/octet-stream", size_bytes=total))
    try:
        db.commit()
    except Exception:
        db.rollback()
        media_path.unlink(missing_ok=True)
        raise
    return {"id": video.id, "title": video.title, "status": video.status, "size_bytes": total,
            "message": "Creator-authorized media is stored. It has not been transcribed or indexed."}


@app.post("/api/videos/{video_id}/process", status_code=202)
def process_uploaded_video(video_id: str, request: Request, background_tasks: BackgroundTasks,
                           db: Session = Depends(get_db)) -> dict:
    from .processing import process_authorized_video, get_ffmpeg_binary
    video = db.get(Video, video_id)
    if video is None:
        raise HTTPException(404, "Video not found")
    require_streamer_owner(db, session_user_id(request), video.streamer_id)
    if db.scalar(select(VideoAsset.id).where(VideoAsset.video_id == video_id)) is None:
        raise HTTPException(409, "Only creator-authorized uploaded media can be processed; Twitch metadata is not raw video access")
    if not os.getenv("OPENAI_API_KEY"):
        raise HTTPException(503, "Add OPENAI_API_KEY before starting transcription and AI extraction")
    if not get_ffmpeg_binary():
        raise HTTPException(503, "FFmpeg is not installed on the API host")
    active = db.scalar(select(ProcessingJob).where(ProcessingJob.video_id == video_id,
                                                   ProcessingJob.status.in_(["queued", "running"])))
    if active:
        raise HTTPException(409, "This video already has an active processing job")
    job = ProcessingJob(video_id=video_id, kind="authorized_media_index", status="queued", job_metadata={})
    video.status = "queued"
    db.add(job)
    db.commit()
    db.refresh(job)
    background_tasks.add_task(process_authorized_video, video.id, job.id)
    return {"job_id": job.id, "video_id": video.id, "status": "queued",
            "message": "Processing is queued. Transcript and review drafts will appear when the job completes."}


@app.get("/api/videos/{video_id}")
def get_video(video_id: str, db: Session = Depends(get_db)) -> dict:
    video = db.get(Video, video_id)
    if video is None:
        raise HTTPException(404, "Video not found")
    streamer = db.get(Streamer, video.streamer_id)
    sources = db.scalars(select(WikiEntrySource).join(WikiEntry, WikiEntry.id == WikiEntrySource.wiki_entry_id)
                         .where(WikiEntrySource.video_id == video.id, WikiEntry.status.in_(PUBLIC_ENTRY_STATUSES))
                         .order_by(WikiEntrySource.start_seconds)).all()
    entries = [db.get(WikiEntry, source.wiki_entry_id) for source in sources]
    return {**video_summary(video), "streamer": streamer.username if streamer else None,
            "moments": [{**entry_summary(db, entry), "start_seconds": source.start_seconds, "end_seconds": source.end_seconds}
                        for source, entry in zip(sources, entries) if entry]}


@app.post("/api/search")
@app.post("/api/search/ask")
def search(request: SearchRequest, db: Session = Depends(get_db)) -> dict:
    streamer = streamer_or_404(db, request.streamer_username)
    entries = db.scalars(select(WikiEntry).where(WikiEntry.streamer_id == streamer.id, WikiEntry.status.in_(PUBLIC_ENTRY_STATUSES))).all()
    words = {w for w in re.findall(r"[a-z0-9']+", request.query.lower()) if len(w) > 2}
    stop = {"when", "where", "what", "with", "from", "this", "that", "did", "does", "have", "been", "show", "find", "tell", "about", "were", "first", "get", "its", "the", "and", "who", "for", "are", "was", "how", "not", "started", "playing", "streamer", "streamers"}
    words -= stop
    scored = []
    keyword_scores: dict[str, float] = {}
    for entry in entries:
        haystack = f"{entry.title} {entry.summary} {entry.body} {entry.category}".lower()
        tokens = set(re.findall(r"[a-z0-9']+", haystack))
        matches = len(words & tokens)
        keyword_scores[entry.id] = matches / max(len(words), 1) if words else 0.0
    mode = "keyword search"
    api_key = os.getenv("OPENAI_API_KEY")
    if api_key and entries:
        try:
            embedding_response = httpx.post("https://api.openai.com/v1/embeddings", timeout=15,
                headers={"Authorization": f"Bearer {api_key}"},
                json={"model": os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small"), "input": request.query})
            embedding_response.raise_for_status()
            query_vector = embedding_response.json()["data"][0]["embedding"]
            vectors: dict[str, list[float]] = {}
            similarities: dict[str, float] = {}
            entry_ids = [entry.id for entry in entries]
            if engine.dialect.name == "postgresql":
                statement = text("SELECT owner_id, 1 - (vector_json <=> CAST(:vector AS vector)) AS score "
                                 "FROM embeddings WHERE owner_type=:owner_type AND owner_id IN :ids "
                                 "ORDER BY vector_json <=> CAST(:vector AS vector) LIMIT :limit").bindparams(bindparam("ids", expanding=True))
                rows = db.execute(statement, {"vector": "[" + ",".join(map(str, query_vector)) + "]",
                                              "owner_type": "wiki_entry", "ids": entry_ids, "limit": request.limit})
                similarities = {row.owner_id: float(row.score) for row in rows}
            else:
                stored = db.scalars(select(Embedding).where(Embedding.owner_type == "wiki_entry",
                                                            Embedding.owner_id.in_(entry_ids))).all()
                vectors = {item.owner_id: list(item.vector_json) for item in stored}
                for owner_id, vector in vectors.items():
                    if len(vector) != len(query_vector):
                        continue
                    dot = sum(float(a) * float(b) for a, b in zip(query_vector, vector))
                    norm_a = math.sqrt(sum(float(a) ** 2 for a in query_vector))
                    norm_b = math.sqrt(sum(float(b) ** 2 for b in vector))
                    similarities[owner_id] = dot / (norm_a * norm_b) if norm_a and norm_b else -1.0
            if similarities:
                for entry in entries:
                    cosine = similarities.get(entry.id, -1.0)
                    if cosine >= 0.2:
                        score = max(0.0, min(1.0, (cosine + 1) / 2)) * 0.8 + keyword_scores[entry.id] * 0.2
                        scored.append((score, entry))
                mode = "semantic search"
        except (httpx.HTTPError, KeyError, IndexError, TypeError, ValueError):
            logger.exception("Query embedding failed; falling back to local keyword retrieval")
            scored.clear()
    if mode == "keyword search":
        scored = [(score, entry) for entry in entries if (score := keyword_scores[entry.id]) > 0]
    scored.sort(key=lambda x: (-x[0], x[1].title))
    results = [{**entry_summary(db, entry), "relevance": round(score, 2)} for score, entry in scored[:request.limit]]
    answer = (results[0]["summary"] + (" This result is synthetic sample content." if results[0]["is_sample"] else "")) if results else "No relevant information found in this streamer's wiki yet."
    return {"answer": answer, "grounded": bool(results), "mode": f"sample {mode}" if streamer.is_sample else mode,
            "results": results, "related": results[1:4]}


@app.post("/api/contributions", status_code=201)
def create_contribution(data: ContributionCreate, db: Session = Depends(get_db)) -> dict:
    streamer = streamer_or_404(db, data.streamer_username)
    if data.wiki_entry_id and db.get(WikiEntry, data.wiki_entry_id) is None:
        raise HTTPException(404, "Wiki entry not found")
    contribution = Contribution(streamer_id=streamer.id, wiki_entry_id=data.wiki_entry_id,
                                contributor_name=data.contributor_name.strip(), kind=data.kind,
                                title=data.title.strip(), body=data.body.strip(), status="pending")
    db.add(contribution)
    db.commit()
    db.refresh(contribution)
    return {"id": contribution.id, "status": contribution.status, "title": contribution.title,
            "message": "Your contribution is queued for community review."}


@app.get("/api/contributions")
def list_contributions(status: Literal["pending", "approved", "rejected"] | None = None, db: Session = Depends(get_db)) -> dict:
    statement = select(Contribution)
    if status:
        statement = statement.where(Contribution.status == status)
    items = db.scalars(statement.order_by(Contribution.created_at.desc()).limit(100)).all()
    return {"items": [{"id": c.id, "title": c.title, "body": c.body, "kind": c.kind,
                       "contributor_name": c.contributor_name, "status": c.status, "created_at": c.created_at,
                       "wiki_entry_id": c.wiki_entry_id} for c in items], "total": len(items)}


@app.patch("/api/contributions/{contribution_id}/review")
def review_contribution(contribution_id: str, data: ContributionReview, x_review_token: str | None = Header(default=None), db: Session = Depends(get_db)) -> dict:
    require_reviewer(x_review_token)
    item = db.get(Contribution, contribution_id)
    if item is None:
        raise HTTPException(404, "Contribution not found")
    item.status = data.status
    item.review_note = data.review_note
    db.commit()
    return {"id": item.id, "status": item.status, "review_note": item.review_note}


@app.get("/api/dashboard/stats")
def dashboard_stats(db: Session = Depends(get_db)) -> dict:
    streamer_count = db.scalar(select(func.count(Streamer.id))) or 0
    sample_streamer_count = db.scalar(select(func.count(Streamer.id)).where(Streamer.is_sample.is_(True))) or 0
    return {"streamers": streamer_count,
            "videos": db.scalar(select(func.count(Video.id))) or 0,
            "wiki_entries": db.scalar(select(func.count(WikiEntry.id)).where(WikiEntry.status.in_(PUBLIC_ENTRY_STATUSES))) or 0,
            "pending_drafts": db.scalar(select(func.count(WikiEntry.id)).where(WikiEntry.status == "pending_review")) or 0,
            "pending_contributions": db.scalar(select(func.count(Contribution.id)).where(Contribution.status == "pending")) or 0,
            "queued_jobs": db.scalar(select(func.count(ProcessingJob.id)).where(ProcessingJob.status == "queued")) or 0,
            "demo_mode": streamer_count > 0 and streamer_count == sample_streamer_count,
            "indexing_enabled": bool(os.getenv("OPENAI_API_KEY") and shutil.which("ffmpeg"))}


@app.get("/api/dashboard/jobs")
def dashboard_jobs(db: Session = Depends(get_db)) -> dict:
    items = db.scalars(select(ProcessingJob).order_by(ProcessingJob.created_at.desc()).limit(50)).all()
    return {"items": [{"id": job.id, "video_id": job.video_id, "kind": job.kind, "status": job.status,
                       "attempts": job.attempts, "error": job.error, "created_at": job.created_at} for job in items],
            "total": len(items), "message": "No media processing jobs are started by sample content."}
