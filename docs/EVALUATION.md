# Evaluation

The project includes a lightweight RAG regression harness for checking answer quality over time. It uses the public API and an API key, so it can run against local Docker Compose, staging, or production.

## Dataset Format

Datasets live in `evals/` as JSON files:

```json
{
  "name": "paper-regression",
  "defaults": {
    "mode": "hybrid",
    "limit": 8,
    "min_sources": 1
  },
  "cases": [
    {
      "id": "methods",
      "question": "What methods does the paper use?",
      "document_id": "replace-with-indexed-document-id",
      "required_answer_terms": ["method"],
      "min_sources": 1
    }
  ]
}
```

Supported case fields mirror `/api/qa/ask`:

- `question`
- `document_id`
- `project_id`
- `document_type`
- `tags`
- `mode`
- `limit`
- `rewrite_query`
- `min_score`
- `required_answer_terms`
- `min_sources`

## Running Evaluations

Create an API key with `qa:read` scope, then set:

```bash
export SRA_API_URL=http://localhost:8000/api
export SRA_API_KEY=sra_your_key_here
```

PowerShell:

```powershell
$env:SRA_API_URL = "http://localhost:8000/api"
$env:SRA_API_KEY = "sra_your_key_here"
```

Run the sample dataset:

```bash
python examples/eval_runner.py evals/sample_rag_eval.json --output eval-results.md
```

Fail CI when pass rate drops below a threshold:

```bash
python examples/eval_runner.py evals/sample_rag_eval.json --fail-under 0.8
```

## Scoring

Each case checks:

- The answer is non-empty.
- The answer includes at least `min_sources` citations.
- Every `required_answer_terms` item appears in the answer.

This is intentionally simple and deterministic. For deeper evaluation, add curated datasets with expected document IDs, required evidence terms, and stable source requirements.
