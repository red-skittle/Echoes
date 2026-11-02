from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database import get_db
from app.schemas import SearchQuery, SearchResultItem, AskResponse
from app.services.vector_search import search_knowledge_base, generate_grounded_answer

router = APIRouter(prefix="/api/search", tags=["Search"])

@router.post("", response_model=list[SearchResultItem])
def search(query_data: SearchQuery, db: Session = Depends(get_db)):
    """Semantic and lexical search across wiki entries, events, and transcripts."""
    results = search_knowledge_base(
        db,
        query=query_data.query,
        streamer_id=query_data.streamer_id,
        limit=query_data.limit
    )
    return results

@router.post("/ask", response_model=AskResponse)
def ask_question(query_data: SearchQuery, db: Session = Depends(get_db)):
    """Grounded question answering that never invents timestamps or events."""
    result = generate_grounded_answer(
        db,
        question=query_data.query,
        streamer_id=query_data.streamer_id
    )
    return AskResponse(
        question=result["question"],
        answer=result["answer"],
        is_grounded=result["is_grounded"],
        citations=result["citations"],
        relevant_entries=[]
    )

