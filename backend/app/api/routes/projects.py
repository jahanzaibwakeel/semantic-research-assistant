import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.entities import Document, Project, ResearchNote, SavedQuery, User
from app.schemas.dto import (
    ProjectCreate,
    ProjectRead,
    ResearchNoteCreate,
    ResearchNoteRead,
    SavedQueryCreate,
    SavedQueryRead,
)

router = APIRouter(prefix="/projects", tags=["projects"])


@router.get("", response_model=list[ProjectRead])
def list_projects(user: Annotated[User, Depends(get_current_user)], db: Annotated[Session, Depends(get_db)]):
    return db.scalars(select(Project).where(Project.owner_id == user.id).order_by(Project.created_at.desc())).all()


@router.post("", response_model=ProjectRead, status_code=status.HTTP_201_CREATED)
def create_project(
    payload: ProjectCreate,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    project = Project(owner_id=user.id, name=payload.name, description=payload.description)
    db.add(project)
    db.commit()
    db.refresh(project)
    return project


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_project(
    project_id: uuid.UUID,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    project = _owned_project(db, project_id, user.id)
    for document in db.scalars(select(Document).where(Document.project_id == project.id)).all():
        document.project_id = None
    for saved in db.scalars(select(SavedQuery).where(SavedQuery.project_id == project.id)).all():
        saved.project_id = None
    for note in db.scalars(select(ResearchNote).where(ResearchNote.project_id == project.id)).all():
        note.project_id = None
    db.delete(project)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/saved-queries", response_model=list[SavedQueryRead])
def list_saved_queries(user: Annotated[User, Depends(get_current_user)], db: Annotated[Session, Depends(get_db)]):
    return db.scalars(select(SavedQuery).where(SavedQuery.owner_id == user.id).order_by(SavedQuery.created_at.desc())).all()


@router.post("/saved-queries", response_model=SavedQueryRead, status_code=status.HTTP_201_CREATED)
def create_saved_query(
    payload: SavedQueryCreate,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    if payload.project_id:
        _owned_project(db, payload.project_id, user.id)
    saved = SavedQuery(
        owner_id=user.id,
        project_id=payload.project_id,
        title=payload.title,
        query=payload.query,
        mode=payload.mode,
    )
    db.add(saved)
    db.commit()
    db.refresh(saved)
    return saved


@router.get("/notes", response_model=list[ResearchNoteRead])
def list_notes(user: Annotated[User, Depends(get_current_user)], db: Annotated[Session, Depends(get_db)]):
    return db.scalars(
        select(ResearchNote)
        .where(ResearchNote.owner_id == user.id)
        .order_by(ResearchNote.pinned.desc(), ResearchNote.updated_at.desc())
    ).all()


@router.post("/notes", response_model=ResearchNoteRead, status_code=status.HTTP_201_CREATED)
def create_note(
    payload: ResearchNoteCreate,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    if payload.project_id:
        _owned_project(db, payload.project_id, user.id)
    note = ResearchNote(
        owner_id=user.id,
        project_id=payload.project_id,
        document_id=payload.document_id,
        title=payload.title,
        body=payload.body,
        pinned=payload.pinned,
    )
    db.add(note)
    db.commit()
    db.refresh(note)
    return note


def _owned_project(db: Session, project_id: uuid.UUID, user_id: uuid.UUID) -> Project:
    project = db.get(Project, project_id)
    if not project or project.owner_id != user_id:
        raise HTTPException(status_code=404, detail="Project not found")
    return project
