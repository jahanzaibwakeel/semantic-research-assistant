import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Response
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.entities import EvaluationRecord, UsageRecord, User
from app.schemas.dto import EvaluationRead, UsageSummary
from app.services.exports import project_bibtex, project_markdown_report
from app.services.exports import project_manifest_json

router = APIRouter(prefix="/exports", tags=["exports"])


@router.get("/report.md")
def export_report(
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    project_id: uuid.UUID | None = None,
):
    return Response(
        content=project_markdown_report(db, user.id, project_id),
        media_type="text/markdown",
        headers={"Content-Disposition": 'attachment; filename="research-report.md"'},
    )


@router.get("/bibliography.bib")
def export_bibtex(
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    project_id: uuid.UUID | None = None,
):
    return Response(
        content=project_bibtex(db, user.id, project_id),
        media_type="application/x-bibtex",
        headers={"Content-Disposition": 'attachment; filename="bibliography.bib"'},
    )


@router.get("/manifest.json")
def export_manifest(
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    project_id: uuid.UUID | None = None,
):
    return project_manifest_json(db, user.id, project_id)


@router.get("/usage", response_model=list[UsageSummary])
def usage_summary(user: Annotated[User, Depends(get_current_user)], db: Annotated[Session, Depends(get_db)]):
    rows = db.execute(
        select(
            UsageRecord.operation,
            func.count(UsageRecord.id),
            func.coalesce(func.sum(UsageRecord.estimated_tokens), 0),
        )
        .where(UsageRecord.owner_id == user.id)
        .group_by(UsageRecord.operation)
        .order_by(UsageRecord.operation)
    ).all()
    return [UsageSummary(operation=operation, calls=calls, estimated_tokens=tokens) for operation, calls, tokens in rows]


@router.get("/evaluations", response_model=list[EvaluationRead])
def evaluations(user: Annotated[User, Depends(get_current_user)], db: Annotated[Session, Depends(get_db)]):
    return db.scalars(
        select(EvaluationRecord)
        .where(EvaluationRecord.owner_id == user.id)
        .order_by(EvaluationRecord.created_at.desc())
        .limit(50)
    ).all()
