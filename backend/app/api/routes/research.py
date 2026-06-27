import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.entities import Document, ResearchExtraction, User
from app.schemas.dto import LiteratureMatrixRow, ResearchExtractionRead, ResearchSynthesisRequest
from app.services.research import extract_research_profile, synthesize_literature

router = APIRouter(prefix="/research", tags=["research"])


@router.get("/documents/{document_id}", response_model=ResearchExtractionRead)
def get_document_research(
    document_id: uuid.UUID,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    document = _owned_document(db, document_id, user.id)
    extraction = db.scalar(select(ResearchExtraction).where(ResearchExtraction.document_id == document.id))
    if not extraction:
        raise HTTPException(status_code=404, detail="Research extraction is not available yet")
    return extraction


@router.post("/documents/{document_id}/extract", response_model=ResearchExtractionRead, status_code=status.HTTP_202_ACCEPTED)
def extract_document_research(
    document_id: uuid.UUID,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    document = _owned_document(db, document_id, user.id)
    if document.status not in {"ready", "extracting"}:
        raise HTTPException(status_code=409, detail="Document must be ready before research extraction")
    return extract_research_profile(db, user.id, document)


@router.get("/matrix", response_model=list[LiteratureMatrixRow])
def literature_matrix(
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    rows = db.execute(
        select(Document, ResearchExtraction)
        .join(ResearchExtraction, ResearchExtraction.document_id == Document.id)
        .where(Document.owner_id == user.id, Document.status != "deleted")
        .order_by(Document.created_at.desc())
    ).all()
    return [
        LiteratureMatrixRow(
            document_id=document.id,
            filename=document.filename,
            title=extraction.title or document.title,
            authors=extraction.authors,
            year=extraction.publication_year,
            methods=extraction.methods,
            datasets=extraction.datasets,
            claims=extraction.claims,
            findings=extraction.findings,
            limitations=extraction.limitations,
        )
        for document, extraction in rows
    ]


@router.post("/synthesize")
def synthesize(
    payload: ResearchSynthesisRequest,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    return {"synthesis": synthesize_literature(db, user.id, payload.focus)}


def _owned_document(db: Session, document_id: uuid.UUID, user_id: uuid.UUID) -> Document:
    document = db.get(Document, document_id)
    if not document or document.owner_id != user_id or document.status == "deleted":
        raise HTTPException(status_code=404, detail="Document not found")
    return document
