from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.entities import User
from app.schemas.dto import SearchRequest, SearchResponse
from app.services.rag import semantic_search

router = APIRouter(prefix="/search", tags=["search"])


@router.post("", response_model=SearchResponse)
def search(payload: SearchRequest, user: Annotated[User, Depends(get_current_user)], db: Annotated[Session, Depends(get_db)]):
    results, rewritten_query = semantic_search(
        db,
        user.id,
        payload.query,
        payload.document_id,
        payload.limit,
        payload.mode,
        payload.rewrite_query,
        payload.min_score,
        payload.project_id,
        payload.document_type,
        payload.tags,
    )
    return SearchResponse(
        results=results,
        rewritten_query=rewritten_query if payload.include_rewritten_query else None,
    )
