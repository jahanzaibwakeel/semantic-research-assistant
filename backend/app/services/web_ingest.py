import hashlib
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlparse

import httpx
from fastapi import HTTPException, status

MAX_URL_BYTES = 5 * 1024 * 1024


class ReadableTextParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.skip_depth = 0
        self.parts: list[str] = []

    def handle_starttag(self, tag: str, attrs) -> None:
        if tag in {"script", "style", "noscript", "svg"}:
            self.skip_depth += 1
        if tag in {"p", "br", "li", "h1", "h2", "h3", "article", "section"}:
            self.parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if tag in {"script", "style", "noscript", "svg"} and self.skip_depth:
            self.skip_depth -= 1
        if tag in {"p", "li", "h1", "h2", "h3"}:
            self.parts.append("\n")

    def handle_data(self, data: str) -> None:
        if self.skip_depth:
            return
        text = " ".join(data.split())
        if text:
            self.parts.append(text)

    def text(self) -> str:
        lines = [line.strip() for line in "\n".join(self.parts).splitlines()]
        return "\n".join(line for line in lines if line)


def ingest_url_to_file(url: str, target: Path) -> tuple[str, str, str]:
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise HTTPException(status_code=400, detail="URL must be an absolute HTTP or HTTPS URL")

    try:
        with httpx.Client(timeout=20.0, follow_redirects=True) as client:
            response = client.get(url)
            response.raise_for_status()
            content = response.content
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=400, detail=f"Could not fetch URL: {exc}") from exc

    if len(content) > MAX_URL_BYTES:
        raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="URL response is too large")

    content_type = response.headers.get("content-type", "")
    if "text/html" in content_type:
        parser = ReadableTextParser()
        parser.feed(response.text)
        text = parser.text()
    elif "text/plain" in content_type or "text/markdown" in content_type:
        text = response.text
    else:
        raise HTTPException(status_code=400, detail="URL must return HTML, plain text, or Markdown")

    if len(text.strip()) < 100:
        raise HTTPException(status_code=400, detail="URL did not contain enough readable text")

    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(text, encoding="utf-8")
    checksum = hashlib.sha256(text.encode("utf-8")).hexdigest()
    title = _title_from_html(response.text) or parsed.netloc
    return checksum, "url", title


def _title_from_html(html: str) -> str | None:
    lower = html.lower()
    start = lower.find("<title>")
    end = lower.find("</title>")
    if start == -1 or end == -1 or end <= start:
        return None
    return " ".join(html[start + 7:end].split())[:500]
