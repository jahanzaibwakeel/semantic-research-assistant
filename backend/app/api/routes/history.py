from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.entities import InteractionHistory, User

router = APIRouter(prefix="/history", tags=["history"])


@router.get("")
def history(user: Annotated[User, Depends(get_current_user)], db: Annotated[Session, Depends(get_db)]):
    rows = db.scalars(
        select(InteractionHistory)
        .where(InteractionHistory.owner_id == user.id)
        .order_by(InteractionHistory.created_at.desc())
        .limit(50)
    ).all()
    return [
        {
            "id": row.id,
            "kind": row.kind,
            "query": row.query,
            "response": row.response,
            "document_id": row.document_id,
            "created_at": row.created_at,
        }
        for row in rows
    ]
