import csv
import io
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.entities import ApiKey, Document, DocumentShare, Team, TeamMember, User
from app.schemas.dto import (
    DocumentRead,
    DocumentShareCreate,
    DocumentShareRead,
    TeamCreate,
    TeamMemberInvite,
    TeamMemberRead,
    TeamPolicyUpdate,
    TeamRead,
)

router = APIRouter(prefix="/teams", tags=["teams"])

MANAGER_ROLES = {"owner", "admin"}
TEAM_ROLES = {"owner", "admin", "member", "viewer"}
SHARE_PERMISSIONS = {"read", "write"}


@router.get("", response_model=list[TeamRead])
def list_teams(user: Annotated[User, Depends(get_current_user)], db: Annotated[Session, Depends(get_db)]):
    return db.scalars(
        select(Team)
        .join(TeamMember, TeamMember.team_id == Team.id)
        .where(TeamMember.user_id == user.id)
        .order_by(Team.updated_at.desc())
    ).all()


@router.post("", response_model=TeamRead, status_code=status.HTTP_201_CREATED)
def create_team(payload: TeamCreate, user: Annotated[User, Depends(get_current_user)], db: Annotated[Session, Depends(get_db)]):
    name = payload.name.strip()
    if not name:
        raise HTTPException(status_code=400, detail="Team name is required")
    team = Team(
        owner_id=user.id,
        name=name[:255],
        description=payload.description,
        allowed_api_scopes=_normalize_scope_policy(payload.allowed_api_scopes),
        api_key_daily_limit=payload.api_key_daily_limit,
    )
    db.add(team)
    db.flush()
    db.add(TeamMember(team_id=team.id, user_id=user.id, role="owner"))
    db.commit()
    db.refresh(team)
    return team


@router.patch("/{team_id}/policy", response_model=TeamRead)
def update_team_policy(
    team_id: uuid.UUID,
    payload: TeamPolicyUpdate,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    team = _manageable_team(db, team_id, user.id)
    if payload.api_key_daily_limit is not None and payload.api_key_daily_limit <= 0:
        raise HTTPException(status_code=400, detail="API key daily limit must be greater than zero")
    team.allowed_api_scopes = _normalize_scope_policy(payload.allowed_api_scopes)
    team.api_key_daily_limit = payload.api_key_daily_limit
    db.commit()
    db.refresh(team)
    return team


@router.get("/{team_id}/members", response_model=list[TeamMemberRead])
def list_members(team_id: uuid.UUID, user: Annotated[User, Depends(get_current_user)], db: Annotated[Session, Depends(get_db)]):
    _team_member(db, team_id, user.id)
    rows = db.execute(
        select(TeamMember, User.email)
        .join(User, User.id == TeamMember.user_id)
        .where(TeamMember.team_id == team_id)
        .order_by(TeamMember.created_at.asc())
    ).all()
    return [
        TeamMemberRead(
            id=member.id,
            team_id=member.team_id,
            user_id=member.user_id,
            email=email,
            role=member.role,
            created_at=member.created_at,
        )
        for member, email in rows
    ]


@router.post("/{team_id}/members", response_model=TeamMemberRead, status_code=status.HTTP_201_CREATED)
def add_member(
    team_id: uuid.UUID,
    payload: TeamMemberInvite,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    _manageable_team(db, team_id, user.id)
    role = payload.role.lower().strip()
    if role not in TEAM_ROLES or role == "owner":
        raise HTTPException(status_code=400, detail="Role must be admin, member, or viewer")
    invited = db.scalar(select(User).where(User.email == payload.email.lower()))
    if not invited:
        raise HTTPException(status_code=404, detail="User must register before they can be added to a team")
    existing = db.scalar(select(TeamMember).where(TeamMember.team_id == team_id, TeamMember.user_id == invited.id))
    if existing:
        existing.role = role
        member = existing
    else:
        member = TeamMember(team_id=team_id, user_id=invited.id, role=role)
        db.add(member)
    db.commit()
    db.refresh(member)
    return TeamMemberRead(id=member.id, team_id=member.team_id, user_id=member.user_id, email=invited.email, role=member.role, created_at=member.created_at)


@router.get("/{team_id}/documents", response_model=list[DocumentRead])
def list_team_documents(team_id: uuid.UUID, user: Annotated[User, Depends(get_current_user)], db: Annotated[Session, Depends(get_db)]):
    _team_member(db, team_id, user.id)
    return db.scalars(
        select(Document)
        .join(DocumentShare, DocumentShare.document_id == Document.id)
        .where(DocumentShare.team_id == team_id, Document.status != "deleted")
        .order_by(Document.created_at.desc())
    ).all()


@router.post("/{team_id}/documents", response_model=DocumentShareRead, status_code=status.HTTP_201_CREATED)
def share_document(
    team_id: uuid.UUID,
    payload: DocumentShareCreate,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    _manageable_team(db, team_id, user.id)
    permission = payload.permission.lower().strip()
    if permission not in SHARE_PERMISSIONS:
        raise HTTPException(status_code=400, detail="Permission must be read or write")
    document = db.get(Document, payload.document_id)
    if not document or document.owner_id != user.id or document.status == "deleted":
        raise HTTPException(status_code=404, detail="Document not found")
    share = db.scalar(select(DocumentShare).where(DocumentShare.team_id == team_id, DocumentShare.document_id == document.id))
    if share:
        share.permission = permission
    else:
        share = DocumentShare(team_id=team_id, document_id=document.id, permission=permission)
        db.add(share)
    db.commit()
    db.refresh(share)
    return _share_read(share, document)


@router.delete("/{team_id}/documents/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
def unshare_document(
    team_id: uuid.UUID,
    document_id: uuid.UUID,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    _manageable_team(db, team_id, user.id)
    share = db.scalar(select(DocumentShare).where(DocumentShare.team_id == team_id, DocumentShare.document_id == document_id))
    if not share:
        raise HTTPException(status_code=404, detail="Document share not found")
    document = db.get(Document, document_id)
    if not document or document.owner_id != user.id:
        raise HTTPException(status_code=404, detail="Document not found")
    db.delete(share)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/{team_id}/audit.csv")
def export_team_audit(team_id: uuid.UUID, user: Annotated[User, Depends(get_current_user)], db: Annotated[Session, Depends(get_db)]):
    team = _manageable_team(db, team_id, user.id)
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["section", "id", "name_or_email", "role_or_permission", "metadata"])
    for member, email in db.execute(select(TeamMember, User.email).join(User, User.id == TeamMember.user_id).where(TeamMember.team_id == team_id)).all():
        writer.writerow(["member", member.user_id, email, member.role, f"joined={member.created_at.isoformat()}"])
    for share, document in db.execute(select(DocumentShare, Document).join(Document, Document.id == DocumentShare.document_id).where(DocumentShare.team_id == team_id)).all():
        writer.writerow(["document", document.id, document.title or document.filename, share.permission, f"status={document.status};owner={document.owner_id}"])
    for key in db.scalars(select(ApiKey).where(ApiKey.team_id == team_id)).all():
        writer.writerow(["api_key", key.id, key.name, key.scopes, f"limit={key.daily_request_limit};revoked={key.revoked};requests_today={key.requests_today}"])
    writer.writerow(["policy", team.id, team.name, team.allowed_api_scopes, f"api_key_daily_limit={team.api_key_daily_limit}"])
    return Response(
        output.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{team.name[:40] or "team"}-audit.csv"'},
    )


def _team_member(db: Session, team_id: uuid.UUID, user_id: uuid.UUID) -> TeamMember:
    member = db.scalar(select(TeamMember).where(TeamMember.team_id == team_id, TeamMember.user_id == user_id))
    if not member:
        raise HTTPException(status_code=404, detail="Team not found")
    return member


def _manageable_team(db: Session, team_id: uuid.UUID, user_id: uuid.UUID) -> Team:
    member = _team_member(db, team_id, user_id)
    if member.role not in MANAGER_ROLES:
        raise HTTPException(status_code=403, detail="Team admin role required")
    team = db.get(Team, team_id)
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")
    return team


def _normalize_scope_policy(value: str) -> str:
    scopes = sorted({scope.strip() for scope in value.split(",") if scope.strip()})
    return ",".join(scopes) if scopes else "*"


def _share_read(share: DocumentShare, document: Document) -> DocumentShareRead:
    return DocumentShareRead(
        id=share.id,
        team_id=share.team_id,
        document_id=share.document_id,
        filename=document.filename,
        title=document.title,
        permission=share.permission,
        created_at=share.created_at,
    )
