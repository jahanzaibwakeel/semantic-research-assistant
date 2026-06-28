import uuid
from datetime import datetime, timezone
from typing import Annotated

import jwt
from fastapi import Depends, Header, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.security import decode_token, hash_token
from app.db.session import get_db
from app.models.entities import ApiKey, User

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login", auto_error=False)

ALL_API_KEY_SCOPES = [
    "documents:read",
    "documents:write",
    "search:read",
    "qa:read",
    "research:read",
    "research:write",
    "projects:read",
    "projects:write",
    "exports:read",
    "history:read",
    "ops:read",
    "profile:read",
]


def get_current_user(
    request: Request,
    token: Annotated[str | None, Depends(oauth2_scheme)],
    db: Annotated[Session, Depends(get_db)],
    api_key: Annotated[str | None, Header(alias="X-API-Key")] = None,
) -> User:
    if token:
        return _user_from_jwt(token, db)
    if api_key:
        return _user_from_api_key(api_key, db, request)
    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing credentials")


def _user_from_jwt(token: str, db: Session) -> User:
    try:
        payload = decode_token(token)
    except jwt.PyJWTError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token") from exc

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    try:
        parsed_user_id = uuid.UUID(user_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token") from exc

    user = db.get(User, parsed_user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    return user


def _user_from_api_key(api_key: str, db: Session, request: Request) -> User:
    stored = db.scalar(select(ApiKey).where(ApiKey.key_hash == hash_token(api_key), ApiKey.revoked.is_(False)))
    if not stored:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API key")
    _enforce_api_key_scope(stored, request)
    _enforce_api_key_quota(stored)
    user = db.get(User, stored.owner_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API key")
    stored.last_used_at = datetime.now(timezone.utc)
    db.commit()
    return user


def _enforce_api_key_scope(api_key: ApiKey, request: Request) -> None:
    required = _required_scope(request)
    if required is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="API keys cannot manage account credentials or API keys")
    granted = {scope.strip() for scope in (api_key.scopes or "").split(",") if scope.strip()}
    if "*" in granted or required in granted:
        return
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=f"API key is missing required scope: {required}")


def _enforce_api_key_quota(api_key: ApiKey) -> None:
    now = datetime.now(timezone.utc)
    if api_key.quota_reset_at is None or api_key.quota_reset_at.date() != now.date():
        api_key.requests_today = 0
        api_key.quota_reset_at = now
    if api_key.daily_request_limit is not None and api_key.requests_today >= api_key.daily_request_limit:
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="API key daily request limit exceeded")
    api_key.requests_today += 1


def _required_scope(request: Request) -> str | None:
    path = request.url.path
    method = request.method.upper()
    if path.startswith("/api/admin") or path.startswith("/api/auth/api-keys") or path.startswith("/api/auth/change-password") or path.startswith("/api/auth/logout"):
        return None
    if path.startswith("/api/auth/me"):
        return "profile:read"
    if path.startswith("/api/documents"):
        return "documents:write" if method in {"POST", "PATCH", "DELETE"} else "documents:read"
    if path.startswith("/api/search"):
        return "search:read"
    if path.startswith("/api/qa"):
        return "qa:read"
    if path.startswith("/api/research"):
        return "research:write" if method == "POST" else "research:read"
    if path.startswith("/api/projects"):
        return "projects:write" if method in {"POST", "PATCH", "DELETE"} else "projects:read"
    if path.startswith("/api/exports"):
        return "exports:read"
    if path.startswith("/api/history"):
        return "history:read"
    if path.startswith("/api/ops") or path.startswith("/api/metrics"):
        return "ops:read"
    return "profile:read"


def settings_dep():
    return get_settings()
