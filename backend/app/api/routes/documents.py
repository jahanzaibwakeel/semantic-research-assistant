import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, HTTPException, Response, UploadFile, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.config import Settings, get_settings
from app.db.session import get_db
from app.models.entities import Document, EvaluationRecord, InteractionHistory, Project, ResearchExtraction, ResearchNote, UsageRecord, User
from app.schemas.dto import BulkDocumentAction, DocumentRead, DocumentUpdate, UrlIngestRequest
from app.services.qdrant_store import QdrantStore
from app.services.storage import StorageService
from app.services.uploads import persist_upload, scan_file
from app.services.web_ingest import ingest_url_to_file
from app.workers.tasks import process_document

router = APIRouter(prefix="/documents", tags=["documents"])


@router.get("", response_model=list[DocumentRead])
def list_documents(
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    project_id: uuid.UUID | None = None,
    include_deleted: bool = False,
):
    filters = [Document.owner_id == user.id]
    if not include_deleted:
        filters.append(Document.status != "deleted")
    if project_id:
        filters.append(Document.project_id == project_id)
    return db.scalars(
        select(Document)
        .where(*filters)
        .order_by(Document.created_at.desc())
    ).all()


@router.post("", response_model=DocumentRead, status_code=status.HTTP_202_ACCEPTED)
def upload_document(
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    file: UploadFile = File(...),
    project_id: uuid.UUID | None = Form(default=None),
    tags: str | None = Form(default=None),
    settings: Settings = Depends(get_settings),
):
    if project_id:
        project = db.get(Project, project_id)
        if not project or project.owner_id != user.id:
            raise HTTPException(status_code=404, detail="Project not found")

    document_id = uuid.uuid4()
    suffix = Path(file.filename or "document.pdf").suffix.lower()
    target = settings.upload_dir / str(user.id) / f"{document_id}{suffix}"
    checksum, document_type = persist_upload(file, target, settings.max_upload_mb)

    duplicate = db.scalar(
        select(Document).where(
            Document.owner_id == user.id,
            Document.checksum == checksum,
            Document.status != "deleted",
        )
    )
    if duplicate:
        target.unlink(missing_ok=True)
        raise HTTPException(status_code=409, detail="This document has already been uploaded")

    scan_file(target, settings)
    storage_path = StorageService().upload(target, f"{user.id}/{document_id}{suffix}")

    document = Document(
        id=document_id,
        owner_id=user.id,
        project_id=project_id,
        filename=file.filename or "document.pdf",
        document_type=document_type,
        checksum=checksum,
        title=Path(file.filename or "document.pdf").stem,
        tags=tags,
        storage_path=storage_path,
        status="queued",
    )
    db.add(document)
    db.commit()
    db.refresh(document)
    process_document.delay(str(document.id))
    return document


@router.post("/url", response_model=DocumentRead, status_code=status.HTTP_202_ACCEPTED)
def ingest_url(
    payload: UrlIngestRequest,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    settings: Settings = Depends(get_settings),
):
    if payload.project_id:
        project = db.get(Project, payload.project_id)
        if not project or project.owner_id != user.id:
            raise HTTPException(status_code=404, detail="Project not found")

    document_id = uuid.uuid4()
    target = settings.upload_dir / str(user.id) / f"{document_id}.txt"
    checksum, document_type, inferred_title = ingest_url_to_file(payload.url, target)
    duplicate = db.scalar(
        select(Document).where(
            Document.owner_id == user.id,
            Document.checksum == checksum,
            Document.status != "deleted",
        )
    )
    if duplicate:
        target.unlink(missing_ok=True)
        raise HTTPException(status_code=409, detail="This URL content has already been ingested")

    scan_file(target, settings)
    storage_path = StorageService().upload(target, f"{user.id}/{document_id}.txt")

    title = payload.title or inferred_title
    document = Document(
        id=document_id,
        owner_id=user.id,
        project_id=payload.project_id,
        filename=f"{title[:120]}.txt",
        document_type=document_type,
        source_url=payload.url,
        checksum=checksum,
        title=title,
        tags=payload.tags,
        storage_path=storage_path,
        status="queued",
    )
    db.add(document)
    db.commit()
    db.refresh(document)
    process_document.delay(str(document.id))
    return document


@router.get("/{document_id}", response_model=DocumentRead)
def get_document(
    document_id: uuid.UUID,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    document = db.get(Document, document_id)
    if not document or document.owner_id != user.id:
        raise HTTPException(status_code=404, detail="Document not found")
    if document.status == "deleted":
        raise HTTPException(status_code=404, detail="Document not found")
    return document


@router.patch("/{document_id}", response_model=DocumentRead)
def update_document(
    document_id: uuid.UUID,
    payload: DocumentUpdate,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    document = _owned_document(db, document_id, user.id)
    if "project_id" in payload.model_fields_set and payload.project_id:
        project = db.get(Project, payload.project_id)
        if not project or project.owner_id != user.id:
            raise HTTPException(status_code=404, detail="Project not found")
    if "title" in payload.model_fields_set:
        document.title = payload.title
    if "tags" in payload.model_fields_set:
        document.tags = payload.tags
    if "project_id" in payload.model_fields_set:
        document.project_id = payload.project_id
    if document.indexed_at:
        QdrantStore().update_document_metadata(document.id, document.project_id, document.tags)
    db.commit()
    db.refresh(document)
    return document


@router.post("/{document_id}/reprocess", response_model=DocumentRead, status_code=status.HTTP_202_ACCEPTED)
def reprocess_document(
    document_id: uuid.UUID,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    document = _owned_document(db, document_id, user.id)
    if document.status in {"queued", "processing", "summarizing"}:
        raise HTTPException(status_code=409, detail="Document is already being processed")
    if not _storage_exists(document):
        raise HTTPException(status_code=409, detail="Original PDF is no longer available")

    QdrantStore().delete_document(document.id)
    document.status = "queued"
    document.error_message = None
    document.summary = None
    document.key_points = None
    document.processed_at = None
    document.indexed_at = None
    document.page_count = 0
    document.chunk_count = 0
    existing_extraction = db.scalar(select(ResearchExtraction).where(ResearchExtraction.document_id == document.id))
    if existing_extraction:
        db.delete(existing_extraction)
    db.commit()
    db.refresh(document)
    process_document.delay(str(document.id))
    return document


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_document(
    document_id: uuid.UUID,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    document = _owned_document(db, document_id, user.id)
    QdrantStore().delete_document(document.id)
    document.status = "deleted"
    document.deleted_at = datetime.now(timezone.utc)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/{document_id}/restore", response_model=DocumentRead)
def restore_document(
    document_id: uuid.UUID,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    document = db.get(Document, document_id)
    if not document or document.owner_id != user.id or document.status != "deleted":
        raise HTTPException(status_code=404, detail="Deleted document not found")
    if not _storage_exists(document):
        raise HTTPException(status_code=409, detail="Original file is not available; purge this record instead")
    document.status = "queued"
    document.deleted_at = None
    db.commit()
    db.refresh(document)
    process_document.delay(str(document.id))
    return document


@router.delete("/{document_id}/purge", status_code=status.HTTP_204_NO_CONTENT)
def purge_document(
    document_id: uuid.UUID,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    document = db.get(Document, document_id)
    if not document or document.owner_id != user.id:
        raise HTTPException(status_code=404, detail="Document not found")
    _purge_document(db, document)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/bulk/{action}")
def bulk_documents(
    action: str,
    payload: BulkDocumentAction,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    if action not in {"delete", "reprocess", "purge"}:
        raise HTTPException(status_code=400, detail="Bulk action must be delete, reprocess, or purge")
    documents = db.scalars(select(Document).where(Document.owner_id == user.id, Document.id.in_(payload.document_ids))).all()
    count = 0
    for document in documents:
        if action == "delete" and document.status != "deleted":
            QdrantStore().delete_document(document.id)
            document.status = "deleted"
            document.deleted_at = datetime.now(timezone.utc)
            count += 1
        elif action == "reprocess" and document.status != "deleted":
            QdrantStore().delete_document(document.id)
            document.status = "queued"
            document.error_message = None
            document.processed_at = None
            document.indexed_at = None
            process_document.delay(str(document.id))
            count += 1
        elif action == "purge":
            _purge_document(db, document)
            count += 1
    db.commit()
    return {"action": action, "count": count}


def _owned_document(db: Session, document_id: uuid.UUID, user_id: uuid.UUID) -> Document:
    document = db.get(Document, document_id)
    if not document or document.owner_id != user_id or document.status == "deleted":
        raise HTTPException(status_code=404, detail="Document not found")
    return document


def _purge_document(db: Session, document: Document) -> None:
    QdrantStore().delete_document(document.id)
    StorageService().delete(document.storage_path)
    for model in (ResearchExtraction, ResearchNote, UsageRecord, EvaluationRecord, InteractionHistory):
        for row in db.scalars(select(model).where(model.document_id == document.id)).all():
            db.delete(row)
    db.delete(document)


def _storage_exists(document: Document) -> bool:
    if document.storage_path.startswith("s3://"):
        return True
    return Path(document.storage_path).exists()
