# Deployment Runbook

## Local Production-Like Stack

1. Copy `.env.example` to `.env`.
2. Set `SECRET_KEY`, `ADMIN_EMAILS`, `APP_DOMAIN`, `ACME_EMAIL`, model credentials, and `RATE_LIMIT_BACKEND=redis`.
3. Start the production-style stack:

```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml up --build -d
```

## Services

- Caddy reverse proxy on ports `80` and `443`
- Frontend on internal `frontend:3000`
- Backend on internal `backend:8000`
- Postgres, Redis, Qdrant, and optional MinIO object storage

## Backups

```powershell
powershell -ExecutionPolicy Bypass -File scripts/backup.ps1
```

Restore Postgres:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/restore-postgres.ps1 -SqlFile backups/<timestamp>/postgres.sql
```

## Health And Metrics

- Liveness: `/health`
- Readiness: `/health/ready`
- Metrics: `/api/metrics`
- Operational status: `/api/ops/status`

## Scaling Notes

- Use `RATE_LIMIT_BACKEND=redis` before horizontal backend scaling.
- Scale Celery workers independently for document-heavy workloads.
- Prefer managed Postgres, Redis, Qdrant, and S3-compatible storage for production.
- Enable `FILE_SCAN_ENABLED=true` and set `FILE_SCAN_COMMAND` to your scanner wrapper before accepting public uploads.

## Security Checklist

- Use HTTPS with a real `APP_DOMAIN`.
- Rotate `SECRET_KEY`.
- Set `ADMIN_EMAILS` to a small list of trusted operators.
- Restrict `CORS_ORIGINS`.
- Keep `SECURITY_HEADERS_ENABLED=true` unless another edge proxy owns those headers.
- Keep `.env` out of git.
- Use logout-all after suspected account compromise to revoke outstanding refresh sessions.
- Review URL ingestion policy before opening the app to untrusted users.
- Run malware scanning for both uploaded files and URL-ingested content before document processing.
