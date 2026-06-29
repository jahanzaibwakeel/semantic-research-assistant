# AI Semantic Research Assistant

A production-style full-stack research workspace built with FastAPI, LangChain, Qdrant, PostgreSQL, Redis/Celery, and Next.js.

Users can register, upload PDFs, index papers into Qdrant, run semantic search, ask cited questions across one or all documents, generate summaries/key research points, and compare two documents.

## Architecture

- `backend/`: FastAPI API, SQLAlchemy metadata models, JWT auth, LangChain RAG services, Qdrant integration, Celery worker tasks.
- `frontend/`: Next.js + React + TypeScript dashboard for uploads, document status, semantic search, Q&A, summaries, and comparisons.
- `postgres`: stores users, document metadata, summaries, and interaction history.
- `redis`: Celery broker/result backend.
- `qdrant`: vector database for chunk embeddings and payload metadata.

Deeper docs:

- [Architecture](docs/ARCHITECTURE.md)
- [API Usage](docs/API_USAGE.md)
- [Evaluation](docs/EVALUATION.md)
- [Deployment Runbook](DEPLOYMENT.md)
- [Roadmap](docs/ROADMAP.md)
- [Contributing](CONTRIBUTING.md)
- [Security](SECURITY.md)

## Features

- JWT registration/login with protected API routes.
- Refresh-token rotation for longer-lived sessions.
- Logout, logout-all, and password change flows with refresh-token revocation.
- Scoped API keys with optional daily request limits for programmatic ingestion, search, Q&A, exports, and automation.
- Standard-library Python CLI example for API-key workflows.
- Memory or Redis-backed per-IP rate limiting for API abuse protection.
- Security response headers for production browser hardening.
- Project workspaces for grouping documents and research notes.
- Admin operations panel for configured admins with user, failed-job, and storage visibility.
- Saved queries and pinned research notes.
- Usage tracking with estimated token counts by operation.
- Automatic citation coverage and groundedness evaluation records.
- API-driven RAG regression evaluation runner with JSON/Markdown reports.
- Markdown research report export.
- BibTeX bibliography export.
- Optional S3-compatible object storage with MinIO in Docker Compose.
- Streaming Q&A endpoint and frontend streaming button.
- Browser-based source preview for PDFs, text, and Markdown with highlighted citation excerpts.
- Scanned-PDF detection hook for OCR workflows.
- PDF, TXT, Markdown, and URL ingestion with metadata tracking.
- LangChain `PyPDFLoader` text extraction.
- Plain-text and Markdown document ingestion.
- HTTP/HTTPS web article ingestion with readable-text extraction.
- LangChain recursive text splitting.
- OpenAI or local sentence-transformer embeddings.
- Qdrant vector storage with per-user and per-document filters.
- Semantic search with page/chunk citations.
- Document Q&A using retrieved context and source citations.
- Hybrid retrieval with vector search, keyword matching, score fusion, and lightweight reranking.
- Query rewriting for better retrieval on vague research questions.
- Filtered retrieval by project, source type, and required tags.
- Editable document title, project assignment, and tags with Qdrant payload metadata sync.
- Configurable relevance threshold and chunking settings.
- Citation guardrails for unsupported or weak-context answers.
- Background parsing, chunking, embedding, and summarization with Celery.
- Structured summaries covering key points, claims, methods, limitations, and findings.
- Two-document comparison workflow.
- Research profile extraction for title, authors, venue, DOI, abstract, methods, datasets, claims, evidence, findings, limitations, future work, and implications.
- Literature matrix view across extracted papers.
- AI-generated literature synthesis from the matrix.
- Annotated bibliography text for each extracted paper.
- Chat/search/compare history persistence.
- Docker Compose stack for API, UI, worker, PostgreSQL, Redis, and Qdrant.
- Production Compose override with Caddy reverse proxy.
- Backup, restore, and maintenance PowerShell scripts.
- Prometheus-style metrics endpoint.
- Optional OpenTelemetry tracing for FastAPI, SQLAlchemy, Redis, Celery, Qdrant, embeddings, and LLM calls.
- GitHub Actions CI with backend, frontend, and Docker build checks.
- Alembic migrations applied automatically by the backend container.
- PDF size, extension, content type, file signature, and duplicate-upload validation.
- Optional command-based antivirus/malware scan hook before storage and processing.
- Document reprocess and soft-delete lifecycle actions.
- Deleted document restore and permanent purge workflows.
- Bulk document actions for delete, reprocess, and purge.
- Worker retry/backoff with visible `retrying` and `failed` states.
- Request logging with request IDs.

## Quick Start

1. Copy environment variables:

```bash
cp .env.example .env
```

2. Set `OPENAI_API_KEY` in `.env`, or set `LLM_PROVIDER=ollama` and make sure Ollama is running with the configured model.

3. Start the stack:

```bash
docker compose up --build
```

4. Open the app:

- Frontend: http://localhost:3000
- Backend health: http://localhost:8000/health
- Backend readiness: http://localhost:8000/health/ready
- MinIO console: http://localhost:9001
- API docs: http://localhost:8000/docs
- Qdrant dashboard/API: http://localhost:6333/dashboard
- Deployment runbook: `DEPLOYMENT.md`

Production-style stack:

```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml up --build -d
```

## Local Development

Backend:

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload
```

Worker:

```bash
cd backend
celery -A app.workers.celery_app.celery_app worker --loglevel=INFO -Q documents
```

Frontend:

```bash
cd frontend
npm install
npm run dev
```

Backend tests:

```bash
cd backend
pip install -r requirements.txt
python -m unittest discover tests
```

## Important Environment Variables

- `SECRET_KEY`: JWT signing secret.
- `ADMIN_EMAILS`: JSON list of user emails allowed to access admin operations.
- `REFRESH_TOKEN_EXPIRE_DAYS`: refresh token lifetime.
- `RATE_LIMIT_REQUESTS`: max requests per IP per rate-limit window.
- `RATE_LIMIT_WINDOW_SECONDS`: rate-limit window duration.
- `RATE_LIMIT_BACKEND`: `memory` for local dev or `redis` for distributed deployments.
- `SECURITY_HEADERS_ENABLED`: toggles hardened browser response headers.
- `OTEL_ENABLED`: enables OpenTelemetry tracing.
- `OTEL_SERVICE_NAME`: service name attached to emitted traces.
- `OTEL_EXPORTER_OTLP_ENDPOINT`: OTLP gRPC endpoint, for example an OpenTelemetry Collector.
- `DATABASE_URL`: SQLAlchemy PostgreSQL URL.
- `REDIS_URL`: Redis broker/backend URL.
- `QDRANT_URL`: Qdrant HTTP URL.
- `LLM_PROVIDER`: `openai` or `ollama`.
- `OPENAI_API_KEY`: required when using OpenAI chat or embeddings.
- `EMBEDDING_PROVIDER`: `sentence-transformers` or `openai`.
- `EMBEDDING_MODEL`: embedding model name.
- `MAX_UPLOAD_MB`: maximum accepted PDF size.
- `STORAGE_BACKEND`: `local` or `s3`.
- `S3_ENDPOINT_URL`, `S3_ACCESS_KEY_ID`, `S3_SECRET_ACCESS_KEY`, `S3_BUCKET`, `S3_REGION`: S3/MinIO storage settings.
- `FILE_SCAN_ENABLED`: enables command-based malware scanning before storage and processing.
- `FILE_SCAN_COMMAND`: scanner command, for example `clamscan --no-summary {path}`.
- `FILE_SCAN_TIMEOUT_SECONDS`: scanner timeout.
- `OCR_ENABLED`: enables OCR fallback path once an OCR engine is installed.
- `OCR_MIN_TEXT_CHARS`: scanned-PDF detection threshold.
- `CHUNK_SIZE`: LangChain splitter chunk size.
- `CHUNK_OVERLAP`: LangChain splitter overlap.
- `KEYWORD_CANDIDATE_LIMIT`: number of Qdrant payload chunks scanned for keyword retrieval.
- `VECTOR_CANDIDATE_MULTIPLIER`: multiplier used to collect vector candidates before reranking.
- `MIN_RELEVANCE_SCORE`: default retrieval cutoff.
- `CORS_ORIGINS`: JSON list of allowed frontend origins.

## API Surface

- `POST /api/auth/register`
- `POST /api/auth/login`
- `POST /api/auth/refresh`
- `POST /api/auth/logout`
- `POST /api/auth/logout-all`
- `POST /api/auth/change-password`
- `GET /api/auth/api-keys`
- `POST /api/auth/api-keys`
- `DELETE /api/auth/api-keys/{api_key_id}`
- `GET /api/auth/me`
- `GET /api/admin/overview`
- `GET /api/projects`
- `POST /api/projects`
- `DELETE /api/projects/{project_id}`
- `GET /api/projects/saved-queries`
- `POST /api/projects/saved-queries`
- `GET /api/projects/notes`
- `POST /api/projects/notes`
- `GET /api/exports/report.md`
- `GET /api/exports/bibliography.bib`
- `GET /api/exports/manifest.json`
- `GET /api/exports/usage`
- `GET /api/exports/evaluations`
- `GET /api/ops/status`
- `GET /api/metrics`
- `POST /api/documents`
- `POST /api/documents/url`
- `GET /api/documents`
- `GET /api/documents/{document_id}`
- `GET /api/documents/{document_id}/file`
- `PATCH /api/documents/{document_id}`
- `POST /api/documents/{document_id}/reprocess`
- `POST /api/documents/{document_id}/restore`
- `DELETE /api/documents/{document_id}`
- `DELETE /api/documents/{document_id}/purge`
- `POST /api/documents/bulk/{action}`
- `POST /api/search`
- `POST /api/qa/ask`
- `POST /api/qa/ask/stream`
- `POST /api/qa/compare`
- `GET /api/research/documents/{document_id}`
- `POST /api/research/documents/{document_id}/extract`
- `GET /api/research/matrix`
- `POST /api/research/synthesize`
- `GET /api/history`
- `GET /health/ready`

## Notes For Production

- Replace `SECRET_KEY` before deployment.
- Put the API behind HTTPS and tighten `CORS_ORIGINS`.
- Add structured JSON-mode extraction when using models that guarantee JSON output.
- Set `RATE_LIMIT_BACKEND=redis` before horizontal scaling.
- Enable `FILE_SCAN_ENABLED` and configure a scanner before public deployments.
- Use managed Qdrant/PostgreSQL/Redis or durable volumes with backup policies.
