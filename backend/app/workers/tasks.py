import uuid
from datetime import datetime, timezone
from pathlib import Path

from app.db.session import SessionLocal
from app.models.entities import Document
from app.services.documents import load_document, split_pages
from app.services.qdrant_store import QdrantStore
from app.services.rag import summarize_document
from app.services.research import extract_research_profile
from app.services.storage import StorageService
from app.workers.celery_app import celery_app


@celery_app.task(bind=True, name="app.workers.tasks.process_document", max_retries=3)
def process_document(self, document_id: str) -> None:
    db = SessionLocal()
    try:
        document = db.get(Document, uuid.UUID(document_id))
        if not document or document.status == "deleted":
            return
        document.status = "processing"
        db.commit()

        local_source = StorageService().download_to_path(
            document.storage_path,
            Path("storage/cache") / str(document.owner_id) / f"{document.id}.{document.document_type}",
        )
        pages = load_document(local_source, document.document_type)
        chunks = split_pages(pages, document.id, document.filename)
        for chunk in chunks:
            chunk.metadata["owner_id"] = str(document.owner_id)
            chunk.metadata["project_id"] = str(document.project_id) if document.project_id else None
            chunk.metadata["tags"] = document.tags
            chunk.metadata["source_url"] = document.source_url
            chunk.metadata["document_type"] = document.document_type

        QdrantStore().upsert_documents(chunks)
        document.page_count = len(pages)
        document.chunk_count = len(chunks)
        document.indexed_at = datetime.now(timezone.utc)
        document.status = "summarizing"
        db.commit()

        summary, key_points = summarize_document(db, document.owner_id, document)
        document.summary = summary
        document.key_points = key_points
        document.status = "extracting"
        db.commit()

        extract_research_profile(db, document.owner_id, document)
        document.status = "ready"
        document.processed_at = datetime.now(timezone.utc)
        db.commit()
    except Exception as exc:
        db.rollback()
        document = db.get(Document, uuid.UUID(document_id))
        if document:
            document.status = "retrying" if self.request.retries < self.max_retries else "failed"
            document.error_message = str(exc)
            db.commit()
        if self.request.retries < self.max_retries:
            raise self.retry(exc=exc, countdown=30 * (self.request.retries + 1)) from exc
        raise
    finally:
        db.close()
