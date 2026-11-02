from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.database import get_db
from app.models import Streamer, Video, WikiEntry, Topic, Entity, Contribution
from app.schemas import (
    StreamerResponse, StreamerDetailResponse, VideoResponse,
    WikiEntryResponse, TopicSchema, EntitySchema
)

router = APIRouter(prefix="/api/streamers", tags=["Streamers"])

@router.get("", response_model=List[StreamerResponse])
def list_streamers(db: Session = Depends(get_db)):
    streamers = db.query(Streamer).all()
    results = []
    for s in streamers:
        v_count = db.query(Video).filter(Video.streamer_id == s.id).count()
        w_count = db.query(WikiEntry).filter(WikiEntry.streamer_id == s.id).count()
        idx_count = db.query(Video).filter(Video.streamer_id == s.id, Video.is_indexed == True).count()
        
        results.append(StreamerResponse(
            id=s.id,
            twitch_id=s.twitch_id,
            username=s.username,
            display_name=s.display_name,
            description=s.description,
            profile_image_url=s.profile_image_url,
            offline_image_url=s.offline_image_url,
            is_live=s.is_live,
            is_verified=s.is_verified,
            follower_count=s.follower_count,
            created_at=s.created_at,
            video_count=v_count,
            wiki_count=w_count,
            indexed_video_count=idx_count
        ))
    return results

@router.get("/{username}", response_model=StreamerDetailResponse)
def get_streamer_by_username(username: str, db: Session = Depends(get_db)):
    streamer = db.query(Streamer).filter(Streamer.username.ilike(username)).first()
    if not streamer:
        raise HTTPException(status_code=404, detail=f"Streamer '{username}' not found")

    v_count = db.query(Video).filter(Video.streamer_id == streamer.id).count()
    w_count = db.query(WikiEntry).filter(WikiEntry.streamer_id == streamer.id).count()
    idx_count = db.query(Video).filter(Video.streamer_id == streamer.id, Video.is_indexed == True).count()

    recent_videos = (
        db.query(Video)
        .filter(Video.streamer_id == streamer.id)
        .order_by(Video.published_at.desc())
        .limit(10)
        .all()
    )

    featured_entries = (
        db.query(WikiEntry)
        .filter(WikiEntry.streamer_id == streamer.id)
        .order_by(WikiEntry.confidence.desc())
        .limit(8)
        .all()
    )

    topics = db.query(Topic).join(Topic.wiki_entries).filter(WikiEntry.streamer_id == streamer.id).distinct().all()
    entities = db.query(Entity).filter(Entity.streamer_id == streamer.id).limit(10).all()

    # Build response with relationships
    entries_responses = []
    for entry in featured_entries:
        entry_topics = [TopicSchema.model_validate(t) for t in entry.topics]
        entry_entities = [EntitySchema.model_validate(e) for e in entry.entities]
        
        # Sources
        sources_list = []
        for src in entry.sources:
            sources_list.append({
                "id": src.id,
                "video_id": src.video_id,
                "start_timestamp": src.start_timestamp,
                "end_timestamp": src.end_timestamp,
                "quote_text": src.quote_text,
                "context_note": src.context_note,
                "video_title": src.video.title if src.video else None,
                "video_thumbnail": src.video.thumbnail_url if src.video else None,
                "twitch_video_id": src.video.twitch_video_id if src.video else None,
            })

        entries_responses.append(WikiEntryResponse(
            id=entry.id,
            streamer_id=entry.streamer_id,
            slug=entry.slug,
            title=entry.title,
            summary=entry.summary,
            content=entry.content,
            category=entry.category,
            confidence=entry.confidence,
            status=entry.status,
            revision=entry.revision,
            created_at=entry.created_at,
            updated_at=entry.updated_at,
            topics=entry_topics,
            entities=entry_entities,
            sources=sources_list,
            related_entries=[]
        ))

    return StreamerDetailResponse(
        id=streamer.id,
        twitch_id=streamer.twitch_id,
        username=streamer.username,
        display_name=streamer.display_name,
        description=streamer.description,
        profile_image_url=streamer.profile_image_url,
        offline_image_url=streamer.offline_image_url,
        is_live=streamer.is_live,
        is_verified=streamer.is_verified,
        follower_count=streamer.follower_count,
        created_at=streamer.created_at,
        video_count=v_count,
        wiki_count=w_count,
        indexed_video_count=idx_count,
        recent_videos=[VideoResponse.model_validate(v) for v in recent_videos],
        featured_entries=entries_responses,
        top_topics=[TopicSchema.model_validate(t) for t in topics],
        top_entities=[EntitySchema.model_validate(e) for e in entities],
    )

@router.get("/{username}/stats")
def get_streamer_stats(username: str, db: Session = Depends(get_db)):
    streamer = db.query(Streamer).filter(Streamer.username.ilike(username)).first()
    if not streamer:
        raise HTTPException(status_code=404, detail="Streamer not found")

    total_videos = db.query(Video).filter(Video.streamer_id == streamer.id).count()
    indexed_videos = db.query(Video).filter(Video.streamer_id == streamer.id, Video.is_indexed == True).count()
    total_seconds = db.query(func.sum(Video.duration_seconds)).filter(Video.streamer_id == streamer.id, Video.is_indexed == True).scalar() or 0
    total_wiki_entries = db.query(WikiEntry).filter(WikiEntry.streamer_id == streamer.id).count()
    total_contributions = db.query(Contribution).filter(Contribution.streamer_id == streamer.id).count()
    pending_contributions = db.query(Contribution).filter(Contribution.streamer_id == streamer.id, Contribution.status == "pending").count()

    return {
        "streamer_username": streamer.username,
        "total_videos": total_videos,
        "indexed_videos": indexed_videos,
        "indexed_hours": round(total_seconds / 3600.0, 1),
        "total_wiki_entries": total_wiki_entries,
        "total_contributions": total_contributions,
        "pending_contributions": pending_contributions,
    }

