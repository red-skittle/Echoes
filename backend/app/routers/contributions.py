import uuid
from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import Contribution, User, Streamer, WikiEntry
from app.schemas import ContributionCreate, ContributionReview, ContributionResponse

router = APIRouter(prefix="/api/contributions", tags=["Contributions"])

@router.get("", response_model=List[ContributionResponse])
def list_contributions(
    streamer_id: Optional[str] = None,
    status: Optional[str] = None,
    db: Session = Depends(get_db)
):
    query = db.query(Contribution)
    if streamer_id:
        query = query.filter(Contribution.streamer_id == streamer_id)
    if status:
        query = query.filter(Contribution.status == status)

    items = query.order_by(Contribution.created_at.desc()).all()

    results = []
    for c in items:
        results.append(ContributionResponse(
            id=c.id,
            streamer_id=c.streamer_id,
            wiki_entry_id=c.wiki_entry_id,
            user_id=c.user_id,
            contribution_type=c.contribution_type,
            title=c.title,
            description=c.description,
            content_diff=c.content_diff,
            status=c.status,
            review_comment=c.review_comment,
            created_at=c.created_at,
            updated_at=c.updated_at,
            user_name=c.user.display_name if c.user else "Anonymous Contributor",
            streamer_name=c.wiki_entry.streamer.display_name if c.wiki_entry and c.wiki_entry.streamer else "Afterlife Community",
            wiki_title=c.wiki_entry.title if c.wiki_entry else "New Article Submission"
        ))
    return results

@router.post("", response_model=ContributionResponse)
def create_contribution(
    data: ContributionCreate,
    user_id: Optional[str] = None,
    db: Session = Depends(get_db)
):
    # Resolve user
    user = None
    if user_id:
        user = db.query(User).filter(User.id == user_id).first()
    if not user:
        user = db.query(User).filter(User.role == "contributor").first()
    if not user:
        user = db.query(User).first()

    streamer = db.query(Streamer).filter(Streamer.id == data.streamer_id).first()
    if not streamer:
        raise HTTPException(status_code=404, detail="Streamer not found")

    contribution = Contribution(
        id=str(uuid.uuid4()),
        streamer_id=data.streamer_id,
        wiki_entry_id=data.wiki_entry_id,
        user_id=user.id,
        contribution_type=data.contribution_type,
        title=data.title,
        description=data.description,
        content_diff=data.content_diff,
        status="pending"
    )
    db.add(contribution)
    db.commit()
    db.refresh(contribution)

    return ContributionResponse(
        id=contribution.id,
        streamer_id=contribution.streamer_id,
        wiki_entry_id=contribution.wiki_entry_id,
        user_id=contribution.user_id,
        contribution_type=contribution.contribution_type,
        title=contribution.title,
        description=contribution.description,
        content_diff=contribution.content_diff,
        status=contribution.status,
        review_comment=contribution.review_comment,
        created_at=contribution.created_at,
        updated_at=contribution.updated_at,
        user_name=user.display_name,
        streamer_name=streamer.display_name,
        wiki_title=contribution.wiki_entry.title if contribution.wiki_entry else "New Article Submission"
    )

@router.patch("/{contribution_id}/review")
def review_contribution(
    contribution_id: str,
    review: ContributionReview,
    db: Session = Depends(get_db)
):
    contrib = db.query(Contribution).filter(Contribution.id == contribution_id).first()
    if not contrib:
        raise HTTPException(status_code=404, detail="Contribution not found")

    contrib.status = review.status
    contrib.review_comment = review.review_comment
    contrib.updated_at = datetime.utcnow()
    
    # If approved and it's a correction on an existing article, bump the revision
    if review.status == "approved" and contrib.wiki_entry:
        contrib.wiki_entry.revision += 1

    db.commit()
    return {"message": f"Contribution marked as {review.status}", "id": contrib.id}

