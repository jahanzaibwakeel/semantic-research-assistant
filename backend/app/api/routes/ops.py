from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.entities import Document, User
from app.schemas.dto import OperationalStatus

router = APIRouter(prefix="/ops", tags=["ops"])


@router.get("/status", response_model=OperationalStatus)
def operational_status(user: Annotated[User, Depends(get_current_user)], db: Annotated[Session, Depends(get_db)]):
    status_rows = db.execute(
        select(Document.status, func.count(Document.id))
        .where(Document.owner_id == user.id)
        .group_by(Document.status)
    ).all()
    type_rows = db.execute(
        select(Document.document_type, func.count(Document.id))
        .where(Document.owner_id == user.id, Document.status != "deleted")
        .group_by(Document.document_type)
    ).all()
    failures = db.scalars(
        select(Document)
        .where(Document.owner_id == user.id, Document.status.in_(["failed", "retrying"]))
        .order_by(Document.updated_at.desc())
        .limit(10)
    ).all()
    return OperationalStatus(
        documents_by_status={status: count for status, count in status_rows},
        documents_by_type={document_type: count for document_type, count in type_rows},
        recent_failures=failures,
    )
