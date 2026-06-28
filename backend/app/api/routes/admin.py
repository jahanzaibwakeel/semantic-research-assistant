from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.config import Settings, get_settings
from app.db.session import get_db
from app.models.entities import ApiKey, Document, User
from app.schemas.dto import AdminFailedJob, AdminOverview, AdminStorageStatus, AdminUserRead

router = APIRouter(prefix="/admin", tags=["admin"])


def require_admin(
    user: Annotated[User, Depends(get_current_user)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> User:
    allowed = {email.lower().strip() for email in settings.admin_emails}
    if not allowed or user.email.lower() not in allowed:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access is not configured for this user")
    return user


@router.get("/overview", response_model=AdminOverview)
def admin_overview(
    _: Annotated[User, Depends(require_admin)],
    db: Annotated[Session, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
):
    users = db.scalars(select(User).order_by(User.created_at.desc()).limit(100)).all()
    document_counts = dict(db.execute(select(Document.owner_id, func.count(Document.id)).group_by(Document.owner_id)).all())
    api_key_counts = dict(db.execute(select(ApiKey.owner_id, func.count(ApiKey.id)).where(ApiKey.revoked.is_(False)).group_by(ApiKey.owner_id)).all())

    failed_rows = db.execute(
        select(Document, User.email)
        .join(User, User.id == Document.owner_id)
        .where(Document.status.in_(["failed", "retrying"]))
        .order_by(Document.updated_at.desc())
        .limit(20)
    ).all()

    return AdminOverview(
        users=[
            AdminUserRead(
                id=user.id,
                email=user.email,
                full_name=user.full_name,
                document_count=document_counts.get(user.id, 0),
                api_key_count=api_key_counts.get(user.id, 0),
                created_at=user.created_at,
            )
            for user in users
        ],
        failed_jobs=[
            AdminFailedJob(
                document_id=document.id,
                owner_email=email,
                filename=document.filename,
                status=document.status,
                error_message=document.error_message,
                updated_at=document.updated_at,
            )
            for document, email in failed_rows
        ],
        storage=_storage_status(settings),
    )


def _storage_status(settings: Settings) -> AdminStorageStatus:
    files = [path for path in settings.upload_dir.rglob("*") if path.is_file()] if Path(settings.upload_dir).exists() else []
    return AdminStorageStatus(
        backend=settings.storage_backend,
        local_upload_bytes=sum(path.stat().st_size for path in files),
        local_upload_files=len(files),
    )
