from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import WikiEntry, WikiEntrySource, Streamer, Topic, Entity, WikiRelationship, User
from app.schemas import WikiEntryResponse, WikiEntryCreate, TopicSchema, EntitySchema

router = APIRouter(prefix="/api/wiki", tags=["Wiki"])

@router.get("/{slug}", response_model=WikiEntryResponse)
def get_wiki_entry_by_slug(slug: str, db: Session = Depends(get_db)):
    entry = db.query(WikiEntry).filter(WikiEntry.slug == slug).first()
    if not entry:
        raise HTTPException(status_code=404, detail=f"Wiki article '{slug}' not found")

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

    # Related entries
    related = []
    for rel in entry.outbound_relationships:
        target = rel.target_entry
        if target:
            related.append({
                "id": target.id,
                "slug": target.slug,
                "title": target.title,
                "relationship_type": rel.relationship_type,
                "description": rel.description,
                "category": target.category
            })
    for rel in entry.inbound_relationships:
        source = rel.source_entry
        if source:
            related.append({
                "id": source.id,
                "slug": source.slug,
                "title": source.title,
                "relationship_type": f"referenced_by ({rel.relationship_type})",
                "description": rel.description,
                "category": source.category
            })

    return WikiEntryResponse(
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
        topics=[TopicSchema.model_validate(t) for t in entry.topics],
        entities=[EntitySchema.model_validate(e) for e in entry.entities],
        sources=sources_list,
        related_entries=related
    )

@router.get("/streamer/{username}", response_model=List[WikiEntryResponse])
def get_streamer_wiki_entries(
    username: str,
    category: Optional[str] = None,
    topic: Optional[str] = None,
    status: Optional[str] = None,
    db: Session = Depends(get_db)
):
    streamer = db.query(Streamer).filter(Streamer.username.ilike(username)).first()
    if not streamer:
        raise HTTPException(status_code=404, detail="Streamer not found")

    query = db.query(WikiEntry).filter(WikiEntry.streamer_id == streamer.id)
    if category:
        query = query.filter(WikiEntry.category.ilike(category))
    if status:
        query = query.filter(WikiEntry.status == status)
    if topic:
        query = query.join(WikiEntry.topics).filter(Topic.slug == topic)

    entries = query.order_by(WikiEntry.created_at.desc()).all()

    results = []
    for entry in entries:
        sources_list = [
            {
                "id": s.id,
                "video_id": s.video_id,
                "start_timestamp": s.start_timestamp,
                "end_timestamp": s.end_timestamp,
                "quote_text": s.quote_text,
                "context_note": s.context_note,
                "video_title": s.video.title if s.video else None,
                "video_thumbnail": s.video.thumbnail_url if s.video else None,
                "twitch_video_id": s.video.twitch_video_id if s.video else None,
            }
            for s in entry.sources
        ]
        results.append(WikiEntryResponse(
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
            topics=[TopicSchema.model_validate(t) for t in entry.topics],
            entities=[EntitySchema.model_validate(e) for e in entry.entities],
            sources=sources_list,
            related_entries=[]
        ))
    return results

@router.patch("/{entry_id}")
def update_wiki_entry(
    entry_id: str,
    title: Optional[str] = None,
    summary: Optional[str] = None,
    content: Optional[str] = None,
    status: Optional[str] = None,
    db: Session = Depends(get_db)
):
    entry = db.query(WikiEntry).filter(WikiEntry.id == entry_id).first()
    if not entry:
        raise HTTPException(status_code=404, detail="Wiki entry not found")

    if title:
        entry.title = title
    if summary:
        entry.summary = summary
    if content:
        entry.content = content
    if status:
        entry.status = status

    entry.revision += 1
    db.commit()
    db.refresh(entry)
    return {"message": "Wiki entry updated successfully", "revision": entry.revision}

