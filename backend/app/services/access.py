import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.entities import Document, DocumentShare, TeamMember


def shared_document_ids(db: Session, user_id: uuid.UUID) -> list[uuid.UUID]:
    return list(
        db.scalars(
            select(DocumentShare.document_id)
            .join(TeamMember, TeamMember.team_id == DocumentShare.team_id)
            .where(TeamMember.user_id == user_id)
        ).all()
    )


def get_accessible_document(db: Session, user_id: uuid.UUID, document_id: uuid.UUID, *, ready_only: bool = False) -> Document | None:
    document = db.get(Document, document_id)
    if not document or document.status == "deleted":
        return None
    if ready_only and document.status != "ready":
        return None
    if document.owner_id == user_id:
        return document
    shared = db.scalar(
        select(DocumentShare.id)
        .join(TeamMember, TeamMember.team_id == DocumentShare.team_id)
        .where(DocumentShare.document_id == document_id, TeamMember.user_id == user_id)
    )
    return document if shared else None

