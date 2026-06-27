from typing import Annotated

from fastapi import APIRouter, Depends, Response
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.logging import REQUEST_COUNT, REQUEST_LATENCY_MS
from app.db.session import get_db
from app.models.entities import Document, User

router = APIRouter(prefix="/metrics", tags=["metrics"])


@router.get("")
def metrics(user: Annotated[User, Depends(get_current_user)], db: Annotated[Session, Depends(get_db)]):
    lines = [
        "# HELP app_http_requests_total Total HTTP requests handled by the API.",
        "# TYPE app_http_requests_total counter",
    ]
    for (method, path, status), count in sorted(REQUEST_COUNT.items()):
        lines.append(f'app_http_requests_total{{method="{method}",path="{path}",status="{status}"}} {count}')

    lines.extend(
        [
            "# HELP app_http_request_latency_ms_average Average request latency in milliseconds.",
            "# TYPE app_http_request_latency_ms_average gauge",
        ]
    )
    for (method, path), values in sorted(REQUEST_LATENCY_MS.items()):
        average = sum(values) / max(len(values), 1)
        lines.append(f'app_http_request_latency_ms_average{{method="{method}",path="{path}"}} {average:.2f}')

    status_rows = db.execute(
        select(Document.status, func.count(Document.id))
        .where(Document.owner_id == user.id)
        .group_by(Document.status)
    ).all()
    lines.extend(
        [
            "# HELP app_documents_total Documents owned by the authenticated user by status.",
            "# TYPE app_documents_total gauge",
        ]
    )
    for status, count in status_rows:
        lines.append(f'app_documents_total{{status="{status}"}} {count}')

    return Response("\n".join(lines) + "\n", media_type="text/plain")
