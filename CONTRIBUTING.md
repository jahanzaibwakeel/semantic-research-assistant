# Contributing

Thanks for taking a look at the Semantic Research Assistant. This project is structured as a production-style full-stack RAG application, so contributions should keep backend architecture, frontend usability, and deployment ergonomics in balance.

## Development Setup

1. Copy `.env.example` to `.env`.
2. Configure either OpenAI credentials or Ollama settings.
3. Start dependencies with Docker Compose:

```bash
docker compose up postgres redis qdrant minio
```

4. Run the backend:

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload
```

5. Run the worker:

```bash
cd backend
celery -A app.workers.celery_app.celery_app worker --loglevel=INFO -Q documents
```

6. Run the frontend:

```bash
cd frontend
npm install
npm run dev
```

## Quality Checks

Run these before opening a pull request:

```bash
cd backend
python -m compileall app tests
python -m unittest discover tests
```

```bash
cd frontend
npm run build
```

```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml config --quiet
```

## Contribution Guidelines

- Keep FastAPI route modules thin and put domain logic in `backend/app/services`.
- Prefer LangChain loaders, splitters, and chain primitives where they make the RAG flow clearer.
- Preserve citation behavior for every answer, summary, and comparison feature.
- Keep frontend changes responsive and workflow-focused.
- Add focused tests for authentication, retrieval, ingestion, and lifecycle behavior when changing those paths.
- Do not commit `.env`, uploaded documents, generated exports, or local vector/database volumes.

## Pull Request Checklist

- The change has a clear user-facing or maintainability reason.
- Tests or compile/build checks were run and noted in the PR.
- Any new environment variables are documented in `.env.example` and `README.md`.
- Any operational behavior is reflected in `DEPLOYMENT.md`.
