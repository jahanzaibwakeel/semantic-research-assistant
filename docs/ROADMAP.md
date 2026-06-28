# Roadmap

## Completed

- FastAPI backend with clean service architecture.
- Next.js dashboard for upload, search, Q&A, comparison, exports, and research workflows.
- Admin operations panel for user management visibility, failed jobs, and storage usage.
- JWT authentication with refresh-token rotation and revocation.
- Scoped API keys with optional daily request limits for programmatic access and automation.
- Standard-library Python CLI client for upload, search, Q&A, and URL ingestion.
- PDF, TXT, Markdown, and URL ingestion.
- Command-based antivirus/malware scan hook before document storage and processing.
- LangChain loaders, text splitting, RAG orchestration, and cited answer generation.
- Qdrant vector storage with user/document/project filters.
- PostgreSQL metadata, history, notes, usage, and evaluation records.
- Evaluation datasets and API-based regression runner for retrieval quality checks.
- Redis and Celery background processing.
- Hybrid retrieval, query rewriting, score fusion, and reranking.
- Summaries, key points, structured research extraction, literature matrix, and synthesis.
- Docker Compose development and production stacks.
- Caddy reverse proxy, backup/restore scripts, metrics, and CI.
- OpenTelemetry traces across API, worker, database, Redis, model, and Qdrant operations.

## Next Improvements

- Full OCR pipeline with Tesseract or a managed OCR provider.
- Team workspaces with roles and document sharing.
- Browser-based PDF preview with highlighted cited passages.
- Team-level API key policies and audit exports.
