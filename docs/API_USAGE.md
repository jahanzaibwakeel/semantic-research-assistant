# API Usage

The dashboard is the easiest way to create an API key. Open the app, sign in, create a key from the API Keys panel, choose scopes, optionally set a daily request limit, and copy the generated value once.

API keys are sent with the `X-API-Key` header. JWT bearer tokens still work for browser sessions.

Available scopes include `documents:read`, `documents:write`, `search:read`, `qa:read`, `research:read`, `research:write`, `projects:read`, `projects:write`, `exports:read`, `history:read`, `ops:read`, and `profile:read`. Use `*` for full access.

## Environment

```bash
export SRA_API_URL=http://localhost:8000/api
export SRA_API_KEY=sra_your_key_here
```

PowerShell:

```powershell
$env:SRA_API_URL = "http://localhost:8000/api"
$env:SRA_API_KEY = "sra_your_key_here"
```

## Curl Examples

List documents:

```bash
curl -H "X-API-Key: $SRA_API_KEY" "$SRA_API_URL/documents"
```

Upload a document:

```bash
curl -X POST "$SRA_API_URL/documents" \
  -H "X-API-Key: $SRA_API_KEY" \
  -F "file=@paper.pdf" \
  -F "tags=rag,survey"
```

Run semantic search:

```bash
curl -X POST "$SRA_API_URL/search" \
  -H "X-API-Key: $SRA_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"query":"retrieval augmented generation limitations","mode":"hybrid","limit":5}'
```

Ask a cited question:

```bash
curl -X POST "$SRA_API_URL/qa/ask" \
  -H "X-API-Key: $SRA_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"question":"What are the main findings and limitations?","limit":8}'
```

Ingest a URL:

```bash
curl -X POST "$SRA_API_URL/documents/url" \
  -H "X-API-Key: $SRA_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"url":"https://example.com/article","tags":"web,reference"}'
```

## Python CLI Client

The repository includes a standard-library client in `examples/research_client.py`.

```bash
python examples/research_client.py docs
python examples/research_client.py upload paper.pdf --tags rag,survey
python examples/research_client.py search "transformer limitations"
python examples/research_client.py ask "What evidence supports the main claim?"
python examples/research_client.py ingest-url "https://example.com/article" --tags web
```

The client reads `SRA_API_URL` and `SRA_API_KEY`, and also accepts `--api-url` for one-off calls.

## Response Shape

Search and Q&A responses return citation metadata:

- `document_id`
- `filename`
- `page`
- `chunk_index`
- `score`
- `retrieval_method`
- `excerpt`

Use these fields to build scripts that preserve source traceability.
