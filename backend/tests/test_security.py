import unittest
import uuid
from types import SimpleNamespace

from fastapi import HTTPException

from app.api.routes.auth import _revoke_user_refresh_tokens, change_password
from app.core.config import Settings
from app.core.logging import RateLimitMiddleware
from app.core.security import hash_password, verify_password
from app.models.entities import RefreshToken, User
from app.schemas.dto import PasswordChangeRequest


class _ScalarResult:
    def __init__(self, items):
        self._items = items

    def all(self):
        return self._items


class _FakeSession:
    def __init__(self, tokens):
        self.tokens = tokens
        self.commits = 0

    def scalars(self, _statement):
        return _ScalarResult(self.tokens)

    def commit(self):
        self.commits += 1


class SecuritySettingsTests(unittest.TestCase):
    def test_rate_limit_backend_accepts_memory_and_redis(self):
        self.assertEqual(Settings(rate_limit_backend="memory").rate_limit_backend, "memory")
        self.assertEqual(Settings(rate_limit_backend="REDIS").rate_limit_backend, "redis")

    def test_rate_limit_backend_rejects_unknown_values(self):
        with self.assertRaises(ValueError):
            Settings(rate_limit_backend="filesystem")


class RateLimitTests(unittest.TestCase):
    def test_memory_rate_limiter_blocks_after_configured_limit(self):
        middleware = RateLimitMiddleware(SimpleNamespace())
        middleware.settings = SimpleNamespace(rate_limit_requests=2, rate_limit_window_seconds=60)

        self.assertFalse(middleware._memory_limited("127.0.0.1", 1000.0))
        self.assertFalse(middleware._memory_limited("127.0.0.1", 1001.0))
        self.assertTrue(middleware._memory_limited("127.0.0.1", 1002.0))


class AuthSessionTests(unittest.TestCase):
    def test_revoke_user_refresh_tokens_marks_active_tokens_revoked(self):
        user = User(id=uuid.uuid4(), email="researcher@example.com", hashed_password="hash")
        tokens = [
            RefreshToken(owner_id=user.id, token_hash="a", revoked=False),
            RefreshToken(owner_id=user.id, token_hash="b", revoked=False),
        ]
        db = _FakeSession(tokens)

        _revoke_user_refresh_tokens(db, user)

        self.assertTrue(all(token.revoked for token in tokens))
        self.assertEqual(db.commits, 1)

    def test_change_password_updates_hash_and_revokes_sessions(self):
        user = User(id=uuid.uuid4(), email="researcher@example.com", hashed_password=hash_password("old-password"))
        token = RefreshToken(owner_id=user.id, token_hash="a", revoked=False)
        db = _FakeSession([token])

        response = change_password(PasswordChangeRequest(current_password="old-password", new_password="new-password"), user, db)

        self.assertEqual(response.status_code, 204)
        self.assertTrue(token.revoked)
        self.assertTrue(verify_password("new-password", user.hashed_password))

    def test_change_password_rejects_wrong_current_password(self):
        user = User(id=uuid.uuid4(), email="researcher@example.com", hashed_password=hash_password("old-password"))

        with self.assertRaises(HTTPException) as exc:
            change_password(
                PasswordChangeRequest(current_password="wrong-password", new_password="new-password"),
                user,
                _FakeSession([]),
            )

        self.assertEqual(exc.exception.status_code, 400)


if __name__ == "__main__":
    unittest.main()
