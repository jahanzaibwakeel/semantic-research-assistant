# Security Policy

## Supported Versions

This repository is a portfolio-grade reference implementation. Security fixes should target the main branch unless a release branch is introduced.

## Reporting A Vulnerability

Please do not open public issues for sensitive security reports. Contact the maintainer privately with:

- A short description of the issue.
- Steps to reproduce.
- Affected endpoint, service, or deployment configuration.
- Any relevant logs or screenshots with secrets removed.

## Built-In Security Controls

- JWT access tokens and rotating refresh tokens.
- Logout and logout-all refresh-token revocation.
- Password change flow that revokes active refresh sessions.
- Hashed API keys with scopes and optional daily request limits for programmatic access through the `X-API-Key` header.
- Per-IP rate limiting with memory or Redis backend.
- Security response headers.
- Upload validation for extension, content type, PDF signature, size, and duplicate content.
- Optional command-based malware scanning before uploaded or ingested files are stored and queued.
- Per-user filters on metadata and vector retrieval paths.
- Environment-based secret configuration.

## Deployment Recommendations

- Set a strong `SECRET_KEY`.
- Use HTTPS in front of the API and frontend.
- Restrict `CORS_ORIGINS` to trusted domains.
- Use `RATE_LIMIT_BACKEND=redis` when running more than one backend instance.
- Revoke API keys that are no longer needed or may have been exposed.
- Store uploaded documents in durable private object storage.
- Enable `FILE_SCAN_ENABLED` with a scanner such as ClamAV for public deployments.
- Keep Postgres, Redis, Qdrant, and object storage off the public internet.
- Review URL ingestion rules before enabling public signups.
