import os
import shlex
import subprocess
import uuid
from pathlib import Path

from langchain_community.document_loaders import PyPDFLoader
from langchain_core.documents import Document as LCDocument
from langchain_text_splitters import RecursiveCharacterTextSplitter

from app.core.config import get_settings


def load_pdf(path: Path) -> list[LCDocument]:
    loader = PyPDFLoader(str(path))
    pages = loader.load()
    for index, page in enumerate(pages, start=1):
        page.metadata["page"] = page.metadata.get("page", index - 1) + 1
    return pages


def load_document(path: Path, document_type: str) -> list[LCDocument]:
    if document_type == "pdf":
        pages = load_pdf(path)
        total_chars = sum(len(page.page_content.strip()) for page in pages)
        settings = get_settings()
        if total_chars < settings.ocr_min_text_chars and settings.ocr_enabled:
            return _load_pdf_with_ocr(path, settings.ocr_min_text_chars)
        if total_chars < settings.ocr_min_text_chars:
            raise RuntimeError(
                "PDF text extraction produced very little text. This may be a scanned PDF; enable OCR support to process it."
            )
        return pages
    text = path.read_text(encoding="utf-8", errors="replace")
    return [LCDocument(page_content=text, metadata={"source": str(path), "page": None})]


def _load_pdf_with_ocr(path: Path, min_chars: int) -> list[LCDocument]:
    settings = get_settings()
    if not settings.ocr_command:
        raise RuntimeError("OCR fallback is enabled but OCR_COMMAND is not configured")
    command = _ocr_command_args(settings.ocr_command, path, settings.ocr_language)
    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=settings.ocr_timeout_seconds,
            check=False,
        )
    except FileNotFoundError as exc:
        raise RuntimeError("OCR command was not found. Install Tesseract or update OCR_COMMAND.") from exc
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError(f"OCR command timed out after {settings.ocr_timeout_seconds} seconds") from exc
    if result.returncode != 0:
        detail = (result.stderr or result.stdout or "OCR command failed").strip()
        raise RuntimeError(f"OCR command failed: {detail[:500]}")
    text = result.stdout.strip()
    if len(text) < min_chars:
        raise RuntimeError("OCR completed but produced too little text to index this scanned PDF")
    return [LCDocument(page_content=text, metadata={"source": str(path), "page": 1, "ocr": True})]


def _ocr_command_args(command: str, path: Path, language: str) -> list[str]:
    parts = shlex.split(command, posix=os.name != "nt")
    rendered = [part.replace("{path}", str(path)).replace("{language}", language) for part in parts]
    if not any("{path}" in part for part in parts):
        rendered.append(str(path))
    return rendered


def split_pages(pages: list[LCDocument], document_id: uuid.UUID, filename: str) -> list[LCDocument]:
    settings = get_settings()
    splitter = RecursiveCharacterTextSplitter(chunk_size=settings.chunk_size, chunk_overlap=settings.chunk_overlap)
    chunks = splitter.split_documents(pages)
    for index, chunk in enumerate(chunks):
        chunk.metadata.update(
            {
                "document_id": str(document_id),
                "filename": filename,
                "chunk_index": index,
                "page": chunk.metadata.get("page"),
            }
        )
    return chunks
