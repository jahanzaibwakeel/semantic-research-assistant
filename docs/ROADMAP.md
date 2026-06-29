# Roadmap

## Completed

- FastAPI backend with clean service architecture.
- Next.js dashboard for upload, search, Q&A, comparison, exports, and research workflows.
- Admin operations panel for user management visibility, failed jobs, and storage usage.
- JWT authentication with refresh-token rotation and revocation.
- Scoped API keys with optional daily request limits for programmatic access and automation.
- Standard-library Python CLI client for upload, search, Q&A, and URL ingestion.
- PDF, TXT, Markdown, and URL ingestion.
- Browser-based source preview for PDFs, text, Markdown, and cited passages.
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
- Command-based OCR fallback for scanned PDFs, including Tesseract-compatible configuration.
- Team workspaces with roles, document sharing, shared-document search/Q&A, and source preview.
- Team-bound API key policies with scope/daily-limit caps and CSV audit exports.

## Next Improvements

- Managed OCR provider adapters such as AWS Textract, Azure Document Intelligence, or Google Document AI.
- Email-based team invitations and SSO/SAML for enterprise deployments.
- Fine-grained write permissions for collaborative annotations on shared documents.
