import logging
import time
import uuid
from collections import defaultdict, deque

from fastapi import status
from redis import Redis
from redis.exceptions import RedisError
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

from app.core.config import get_settings

REQUEST_COUNT: dict[tuple[str, str, int], int] = defaultdict(int)
REQUEST_LATENCY_MS: dict[tuple[str, str], list[float]] = defaultdict(list)


def configure_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        logger = logging.getLogger("app.requests")
        request_id = request.headers.get("x-request-id", str(uuid.uuid4()))
        started = time.perf_counter()
        response = await call_next(request)
        elapsed_ms = round((time.perf_counter() - started) * 1000, 2)
        response.headers["x-request-id"] = request_id
        REQUEST_COUNT[(request.method, request.url.path, response.status_code)] += 1
        latencies = REQUEST_LATENCY_MS[(request.method, request.url.path)]
        latencies.append(elapsed_ms)
        if len(latencies) > 200:
            del latencies[:100]
        logger.info(
            "request_completed method=%s path=%s status=%s elapsed_ms=%s request_id=%s",
            request.method,
            request.url.path,
            response.status_code,
            elapsed_ms,
            request_id,
        )
        return response


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app):
        super().__init__(app)
        self.settings = get_settings()
        self.requests = defaultdict(deque)
        self.redis = Redis.from_url(self.settings.redis_url, decode_responses=True) if self.settings.rate_limit_backend == "redis" else None

    async def dispatch(self, request: Request, call_next):
        if request.url.path == "/health":
            return await call_next(request)

        now = time.time()
        key = request.client.host if request.client else "unknown"
        if self.redis and self._redis_limited(key, now):
            return self._limited_response()
        if not self.redis and self._memory_limited(key, now):
            return self._limited_response()
        return await call_next(request)

    def _redis_limited(self, client_key: str, now: float) -> bool:
        assert self.redis is not None
        window = self.settings.rate_limit_window_seconds
        redis_key = f"rate-limit:{client_key}:{int(now // window)}"
        try:
            count = self.redis.incr(redis_key)
            if count == 1:
                self.redis.expire(redis_key, window + 1)
            return count > self.settings.rate_limit_requests
        except RedisError:
            return self._memory_limited(client_key, now)

    def _memory_limited(self, client_key: str, now: float) -> bool:
        bucket = self.requests[client_key]
        while bucket and now - bucket[0] > self.settings.rate_limit_window_seconds:
            bucket.popleft()
        if len(bucket) >= self.settings.rate_limit_requests:
            return True
        bucket.append(now)
        return False

    @staticmethod
    def _limited_response() -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            content={"detail": "Rate limit exceeded. Please slow down and try again."},
        )


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        settings = get_settings()
        if not settings.security_headers_enabled:
            return response

        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "no-referrer")
        response.headers.setdefault("Permissions-Policy", "camera=(), microphone=(), geolocation=()")
        if request.url.path not in {"/docs", "/redoc", "/openapi.json"}:
            response.headers.setdefault("Content-Security-Policy", settings.content_security_policy)
        return response
