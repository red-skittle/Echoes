from typing import List
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import Video, WikiEntry, Contribution, ProcessingJob, Streamer
from app.schemas import ProcessingJobResponse

router = APIRouter(prefix="/api/dashboard", tags=["Dashboard"])

@router.get("/stats")
def get_dashboard_stats(db: Session = Depends(get_db)):
    streamer = db.query(Streamer).first()
    streamer_id = streamer.id if streamer else None

    total_videos = db.query(Video).count()
    indexed_videos = db.query(Video).filter(Video.is_indexed == True).count()
    total_entries = db.query(WikiEntry).count()
    pending_contribs = db.query(Contribution).filter(Contribution.status == "pending").count()
    active_jobs = db.query(ProcessingJob).filter(ProcessingJob.status.in_(["queued", "in_progress"])).count()

    return {
        "streamer_username": streamer.username if streamer else "aria_valkyrie",
        "streamer_name": streamer.display_name if streamer else "Aria Valkyrie",
        "total_videos": total_videos,
        "indexed_videos": indexed_videos,
        "total_wiki_entries": total_entries,
        "pending_contributions": pending_contribs,
        "active_jobs": active_jobs,
        "is_connected_twitch": True,
        "channel_url": f"https://twitch.tv/{streamer.username}" if streamer else "https://twitch.tv"
    }

@router.get("/jobs", response_model=List[ProcessingJobResponse])
def get_dashboard_jobs(db: Session = Depends(get_db)):
    jobs = db.query(ProcessingJob).order_by(ProcessingJob.created_at.desc()).limit(20).all()
    results = []
    for j in jobs:
        results.append(ProcessingJobResponse(
            id=j.id,
            video_id=j.video_id,
            job_type=j.job_type,
            status=j.status,
            progress=j.progress,
            current_step=j.current_step,
            error_message=j.error_message,
            created_at=j.created_at,
            updated_at=j.updated_at,
            video_title=j.video.title if j.video else "Processed Stream"
        ))
    return results

