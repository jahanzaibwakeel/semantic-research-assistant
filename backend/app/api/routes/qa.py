import uuid
import json
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.entities import Document, User
from app.schemas.dto import AnswerResponse, CompareRequest, QuestionRequest
from app.services.ai import get_llm
from app.services.access import get_accessible_document
from app.services.rag import answer_question, compare_documents, retrieve_question_context

router = APIRouter(prefix="/qa", tags=["qa"])


@router.post("/ask", response_model=AnswerResponse)
def ask(payload: QuestionRequest, user: Annotated[User, Depends(get_current_user)], db: Annotated[Session, Depends(get_db)]):
    retrieval_owner_id = user.id
    if payload.document_id:
        document = get_accessible_document(db, user.id, payload.document_id, ready_only=True)
        if not document:
            raise HTTPException(status_code=404, detail="Document not found")
        retrieval_owner_id = document.owner_id
    answer, sources, rewritten_query = answer_question(
        db,
        user.id,
        payload.question,
        payload.document_id,
        payload.limit,
        payload.mode,
        payload.rewrite_query,
        payload.min_score,
        payload.project_id,
        payload.document_type,
        payload.tags,
        retrieval_owner_id,
    )
    return AnswerResponse(answer=answer, sources=sources, rewritten_query=rewritten_query)


@router.post("/ask/stream")
def ask_stream(payload: QuestionRequest, user: Annotated[User, Depends(get_current_user)], db: Annotated[Session, Depends(get_db)]):
    retrieval_owner_id = user.id
    if payload.document_id:
        document = get_accessible_document(db, user.id, payload.document_id, ready_only=True)
        if not document:
            raise HTTPException(status_code=404, detail="Document not found")
        retrieval_owner_id = document.owner_id
    retrieval_query, sources, context = retrieve_question_context(
        user.id,
        payload.question,
        payload.document_id,
        payload.limit,
        payload.mode,
        payload.rewrite_query,
        payload.min_score,
        payload.project_id,
        payload.document_type,
        payload.tags,
        retrieval_owner_id,
    )

    def events():
        yield f"event: metadata\ndata: {json.dumps({'rewritten_query': retrieval_query, 'sources': [source.model_dump(mode='json') for source in sources]})}\n\n"
        if not sources:
            yield "event: token\ndata: I could not find enough relevant context in the indexed documents to answer that confidently.\n\n"
            yield "event: done\ndata: {}\n\n"
            return
        prompt = (
            "You are a precise research assistant. Answer only from the supplied context. "
            "Every factual claim must include inline citations like [1] or [2].\n\n"
            f"Question: {payload.question}\n\nContext:\n{context}"
        )
        for chunk in get_llm().stream(prompt):
            content = getattr(chunk, "content", "") or ""
            if content:
                yield f"event: token\ndata: {json.dumps(content)}\n\n"
        yield "event: done\ndata: {}\n\n"

    return StreamingResponse(events(), media_type="text/event-stream")


@router.post("/compare", response_model=AnswerResponse)
def compare(payload: CompareRequest, user: Annotated[User, Depends(get_current_user)], db: Annotated[Session, Depends(get_db)]):
    left = _accessible_ready_document(db, payload.left_document_id, user.id)
    right = _accessible_ready_document(db, payload.right_document_id, user.id)
    answer, sources, rewritten_query = compare_documents(db, user.id, left, right, payload.focus or "claims, methods, limitations, findings")
    return AnswerResponse(answer=answer, sources=sources, rewritten_query=rewritten_query)


def _accessible_ready_document(db: Session, document_id: uuid.UUID, user_id: uuid.UUID) -> Document:
    document = get_accessible_document(db, user_id, document_id, ready_only=True)
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    return document
