from typing import Annotated
from datetime import datetime, timedelta, timezone
import uuid

from fastapi import APIRouter, Depends, HTTPException, Response, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import ALL_API_KEY_SCOPES, get_current_user
from app.core.config import get_settings
from app.core.security import create_access_token, create_refresh_token, hash_password, hash_token, verify_password
from app.db.session import get_db
from app.models.entities import ApiKey, RefreshToken, Team, TeamMember, User
from app.schemas.dto import ApiKeyCreate, ApiKeyCreated, ApiKeyRead, LogoutRequest, PasswordChangeRequest, RefreshTokenRequest, Token, UserCreate, UserRead

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=Token, status_code=status.HTTP_201_CREATED)
def register(payload: UserCreate, db: Annotated[Session, Depends(get_db)]):
    existing = db.scalar(select(User).where(User.email == payload.email.lower()))
    if existing:
        raise HTTPException(status_code=409, detail="Email already registered")
    user = User(
        email=payload.email.lower(),
        full_name=payload.full_name,
        hashed_password=hash_password(payload.password),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return _issue_tokens(db, user)


@router.post("/login", response_model=Token)
def login(form: Annotated[OAuth2PasswordRequestForm, Depends()], db: Annotated[Session, Depends(get_db)]):
    user = db.scalar(select(User).where(User.email == form.username.lower()))
    if not user or not verify_password(form.password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect email or password")
    return _issue_tokens(db, user)


@router.post("/refresh", response_model=Token)
def refresh(payload: RefreshTokenRequest, db: Annotated[Session, Depends(get_db)]):
    token_hash = hash_token(payload.refresh_token)
    stored = db.scalar(select(RefreshToken).where(RefreshToken.token_hash == token_hash, RefreshToken.revoked.is_(False)))
    if not stored or stored.expires_at < datetime.now(timezone.utc):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")
    user = db.get(User, stored.owner_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")
    stored.revoked = True
    db.commit()
    return _issue_tokens(db, user)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(
    payload: LogoutRequest,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(get_current_user)],
):
    if payload.refresh_token:
        token_hash = hash_token(payload.refresh_token)
        stored = db.scalar(select(RefreshToken).where(RefreshToken.token_hash == token_hash))
        if stored:
            stored.revoked = True
            db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/logout-all", status_code=status.HTTP_204_NO_CONTENT)
def logout_all(user: Annotated[User, Depends(get_current_user)], db: Annotated[Session, Depends(get_db)]):
    _revoke_user_refresh_tokens(db, user)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/change-password", status_code=status.HTTP_204_NO_CONTENT)
def change_password(
    payload: PasswordChangeRequest,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    if not verify_password(payload.current_password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Current password is incorrect")
    if len(payload.new_password) < 8:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="New password must be at least 8 characters")
    user.hashed_password = hash_password(payload.new_password)
    _revoke_user_refresh_tokens(db, user)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/me", response_model=UserRead)
def me(user: Annotated[User, Depends(get_current_user)]):
    return user


@router.get("/api-keys", response_model=list[ApiKeyRead])
def list_api_keys(user: Annotated[User, Depends(get_current_user)], db: Annotated[Session, Depends(get_db)]):
    return db.scalars(select(ApiKey).where(ApiKey.owner_id == user.id).order_by(ApiKey.created_at.desc())).all()


@router.post("/api-keys", response_model=ApiKeyCreated, status_code=status.HTTP_201_CREATED)
def create_api_key(
    payload: ApiKeyCreate,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    name = payload.name.strip()
    if not name:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="API key name is required")
    scopes = _normalize_api_key_scopes(payload.scopes)
    if payload.daily_request_limit is not None and payload.daily_request_limit <= 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Daily request limit must be greater than zero")
    if payload.team_id:
        team = _manageable_team(db, payload.team_id, user.id)
        _enforce_team_api_key_policy(team, scopes, payload.daily_request_limit)
    api_key_value = f"sra_{create_refresh_token()}"
    api_key = ApiKey(
        owner_id=user.id,
        team_id=payload.team_id,
        name=name[:255],
        key_hash=hash_token(api_key_value),
        key_prefix=api_key_value[:12],
        scopes=scopes,
        daily_request_limit=payload.daily_request_limit,
    )
    db.add(api_key)
    db.commit()
    db.refresh(api_key)
    return ApiKeyCreated.model_validate(api_key, from_attributes=True).model_copy(update={"api_key": api_key_value})


@router.delete("/api-keys/{api_key_id}", status_code=status.HTTP_204_NO_CONTENT)
def revoke_api_key(
    api_key_id: uuid.UUID,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    api_key = db.scalar(select(ApiKey).where(ApiKey.id == api_key_id, ApiKey.owner_id == user.id))
    if not api_key:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="API key not found")
    api_key.revoked = True
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


def _revoke_user_refresh_tokens(db: Session, user: User) -> None:
    tokens = db.scalars(select(RefreshToken).where(RefreshToken.owner_id == user.id, RefreshToken.revoked.is_(False))).all()
    for token in tokens:
        token.revoked = True
    db.commit()


def _normalize_api_key_scopes(scopes: list[str]) -> str:
    if not scopes:
        return "*"
    cleaned = sorted({scope.strip() for scope in scopes if scope.strip()})
    if "*" in cleaned:
        return "*"
    invalid = [scope for scope in cleaned if scope not in ALL_API_KEY_SCOPES]
    if invalid:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid API key scopes: {', '.join(invalid)}")
    return ",".join(cleaned)


def _manageable_team(db: Session, team_id: uuid.UUID, user_id: uuid.UUID) -> Team:
    team = db.get(Team, team_id)
    membership = db.scalar(
        select(TeamMember).where(
            TeamMember.team_id == team_id,
            TeamMember.user_id == user_id,
            TeamMember.role.in_(["owner", "admin"]),
        )
    )
    if not team or not membership:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Team not found")
    return team


def _enforce_team_api_key_policy(team: Team, scopes: str, daily_request_limit: int | None) -> None:
    allowed = {scope.strip() for scope in (team.allowed_api_scopes or "*").split(",") if scope.strip()}
    requested = {scope.strip() for scope in scopes.split(",") if scope.strip()}
    if "*" not in allowed and ("*" in requested or not requested.issubset(allowed)):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="API key scopes exceed team policy")
    if team.api_key_daily_limit is not None:
        if daily_request_limit is None or daily_request_limit > team.api_key_daily_limit:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="API key daily limit exceeds team policy")


def _issue_tokens(db: Session, user: User) -> Token:
    settings = get_settings()
    refresh_value = create_refresh_token()
    refresh = RefreshToken(
        owner_id=user.id,
        token_hash=hash_token(refresh_value),
        expires_at=datetime.now(timezone.utc) + timedelta(days=settings.refresh_token_expire_days),
    )
    db.add(refresh)
    db.commit()
    return Token(access_token=create_access_token(str(user.id)), refresh_token=refresh_value, user=user)
