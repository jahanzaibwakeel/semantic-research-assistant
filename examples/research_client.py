#!/usr/bin/env python
"""Small standard-library client for the Semantic Research Assistant API.

Set SRA_API_KEY to an API key created in the dashboard.

Examples:
    python examples/research_client.py docs
    python examples/research_client.py search "transformer limitations"
    python examples/research_client.py ask "What are the main findings?"
    python examples/research_client.py upload paper.pdf --tags rag,survey
"""

from __future__ import annotations

import argparse
import json
import mimetypes
import os
import sys
import uuid
from pathlib import Path
from urllib import error, parse, request


DEFAULT_API_URL = "http://localhost:8000/api"


class ApiError(RuntimeError):
    pass


def api_url(path: str) -> str:
    base_url = os.getenv("SRA_API_URL", DEFAULT_API_URL).rstrip("/")
    return f"{base_url}{path}"


def api_key() -> str:
    value = os.getenv("SRA_API_KEY")
    if not value:
        raise ApiError("Set SRA_API_KEY before calling protected endpoints.")
    return value


def request_json(method: str, path: str, body: dict | None = None, query: dict | None = None):
    url = api_url(path)
    if query:
        url = f"{url}?{parse.urlencode({key: value for key, value in query.items() if value is not None})}"
    data = json.dumps(body).encode("utf-8") if body is not None else None
    headers = {"X-API-Key": api_key(), "Accept": "application/json"}
    if data is not None:
        headers["Content-Type"] = "application/json"
    req = request.Request(url, data=data, headers=headers, method=method)
    return read_response(req)


def request_multipart(path: str, file_path: Path, fields: dict[str, str | None]):
    boundary = f"sra-{uuid.uuid4().hex}"
    chunks: list[bytes] = []
    for name, value in fields.items():
        if not value:
            continue
        chunks.extend(
            [
                f"--{boundary}\r\n".encode(),
                f'Content-Disposition: form-data; name="{name}"\r\n\r\n'.encode(),
                f"{value}\r\n".encode(),
            ]
        )

    content_type = mimetypes.guess_type(file_path.name)[0] or "application/octet-stream"
    chunks.extend(
        [
            f"--{boundary}\r\n".encode(),
            f'Content-Disposition: form-data; name="file"; filename="{file_path.name}"\r\n'.encode(),
            f"Content-Type: {content_type}\r\n\r\n".encode(),
            file_path.read_bytes(),
            b"\r\n",
            f"--{boundary}--\r\n".encode(),
        ]
    )

    req = request.Request(
        api_url(path),
        data=b"".join(chunks),
        headers={
            "X-API-Key": api_key(),
            "Accept": "application/json",
            "Content-Type": f"multipart/form-data; boundary={boundary}",
        },
        method="POST",
    )
    return read_response(req)


def read_response(req: request.Request):
    try:
        with request.urlopen(req, timeout=60) as response:
            content = response.read()
    except error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise ApiError(f"HTTP {exc.code}: {detail}") from exc
    except error.URLError as exc:
        raise ApiError(f"Request failed: {exc.reason}") from exc
    if not content:
        return None
    return json.loads(content)


def print_json(value) -> None:
    print(json.dumps(value, indent=2, ensure_ascii=False))


def cmd_docs(args) -> None:
    print_json(request_json("GET", "/documents", query={"include_deleted": args.include_deleted}))


def cmd_search(args) -> None:
    print_json(
        request_json(
            "POST",
            "/search",
            {
                "query": args.query,
                "document_id": args.document_id,
                "project_id": args.project_id,
                "mode": args.mode,
                "limit": args.limit,
                "rewrite_query": not args.no_rewrite,
            },
        )
    )


def cmd_ask(args) -> None:
    print_json(
        request_json(
            "POST",
            "/qa/ask",
            {
                "question": args.question,
                "document_id": args.document_id,
                "project_id": args.project_id,
                "mode": args.mode,
                "limit": args.limit,
                "rewrite_query": not args.no_rewrite,
            },
        )
    )


def cmd_upload(args) -> None:
    file_path = Path(args.file)
    if not file_path.exists():
        raise ApiError(f"File not found: {file_path}")
    print_json(
        request_multipart(
            "/documents",
            file_path,
            {"project_id": args.project_id, "tags": args.tags},
        )
    )


def cmd_ingest_url(args) -> None:
    print_json(
        request_json(
            "POST",
            "/documents/url",
            {"url": args.url, "title": args.title, "project_id": args.project_id, "tags": args.tags},
        )
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Semantic Research Assistant API client")
    parser.add_argument("--api-url", help="API base URL. Defaults to SRA_API_URL or http://localhost:8000/api")
    subparsers = parser.add_subparsers(required=True)

    docs = subparsers.add_parser("docs", help="List documents")
    docs.add_argument("--include-deleted", action="store_true")
    docs.set_defaults(func=cmd_docs)

    search = subparsers.add_parser("search", help="Semantic or hybrid search")
    search.add_argument("query")
    add_retrieval_args(search)
    search.set_defaults(func=cmd_search)

    ask = subparsers.add_parser("ask", help="Ask a cited question")
    ask.add_argument("question")
    add_retrieval_args(ask)
    ask.set_defaults(func=cmd_ask)

    upload = subparsers.add_parser("upload", help="Upload a PDF, text, or Markdown file")
    upload.add_argument("file")
    upload.add_argument("--project-id")
    upload.add_argument("--tags")
    upload.set_defaults(func=cmd_upload)

    ingest = subparsers.add_parser("ingest-url", help="Ingest an HTTP/HTTPS article")
    ingest.add_argument("url")
    ingest.add_argument("--title")
    ingest.add_argument("--project-id")
    ingest.add_argument("--tags")
    ingest.set_defaults(func=cmd_ingest_url)
    return parser


def add_retrieval_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--document-id")
    parser.add_argument("--project-id")
    parser.add_argument("--mode", choices=["hybrid", "vector", "keyword"], default="hybrid")
    parser.add_argument("--limit", type=int, default=8)
    parser.add_argument("--no-rewrite", action="store_true")


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    if args.api_url:
        os.environ["SRA_API_URL"] = args.api_url
    try:
        args.func(args)
    except ApiError as exc:
        print(exc, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
