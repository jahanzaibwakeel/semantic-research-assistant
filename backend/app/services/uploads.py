import hashlib
import os
import shlex
import subprocess
from pathlib import Path

from fastapi import HTTPException, UploadFile, status

from app.core.config import Settings

PDF_CONTENT_TYPES = {"application/pdf", "application/x-pdf"}
TEXT_CONTENT_TYPES = {"text/plain", "text/markdown", "application/octet-stream"}
PDF_MAGIC = b"%PDF-"
CHUNK_SIZE = 1024 * 1024
SUPPORTED_EXTENSIONS = {".pdf": "pdf", ".txt": "text", ".md": "markdown", ".markdown": "markdown"}


def detect_document_type(file: UploadFile) -> str:
    filename = file.filename or "document.pdf"
    suffix = Path(filename).suffix.lower()
    document_type = SUPPORTED_EXTENSIONS.get(suffix)
    if not document_type:
        raise HTTPException(status_code=400, detail="Supported uploads: PDF, TXT, Markdown")
    if document_type == "pdf" and file.content_type not in PDF_CONTENT_TYPES:
        raise HTTPException(status_code=400, detail="PDF uploads must use a PDF content type")
    if document_type != "pdf" and file.content_type not in TEXT_CONTENT_TYPES:
        raise HTTPException(status_code=400, detail="Text uploads must use a text content type")
    return document_type


def persist_upload(file: UploadFile, target: Path, max_upload_mb: int) -> tuple[str, str]:
    document_type = detect_document_type(file)

    first_bytes = file.file.read(len(PDF_MAGIC))
    if document_type == "pdf" and first_bytes != PDF_MAGIC:
        raise HTTPException(status_code=400, detail="Uploaded file does not look like a valid PDF")

    target.parent.mkdir(parents=True, exist_ok=True)
    checksum = hashlib.sha256()
    checksum.update(first_bytes)
    max_bytes = max_upload_mb * 1024 * 1024
    written = len(first_bytes)

    with target.open("wb") as buffer:
        buffer.write(first_bytes)
        while True:
            chunk = file.file.read(CHUNK_SIZE)
            if not chunk:
                break
            written += len(chunk)
            if written > max_bytes:
                target.unlink(missing_ok=True)
                raise HTTPException(
                    status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                    detail=f"PDF exceeds the {max_upload_mb} MB upload limit",
                )
            checksum.update(chunk)
            buffer.write(chunk)

    return checksum.hexdigest(), document_type


def scan_file(path: Path, settings: Settings) -> None:
    if not settings.file_scan_enabled:
        return
    command = _scan_command(settings.file_scan_command or "", path)
    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=settings.file_scan_timeout_seconds,
            check=False,
        )
    except FileNotFoundError as exc:
        path.unlink(missing_ok=True)
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="File scanner command was not found") from exc
    except subprocess.TimeoutExpired as exc:
        path.unlink(missing_ok=True)
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="File scanner timed out") from exc
    if result.returncode != 0:
        path.unlink(missing_ok=True)
        detail = (result.stdout or result.stderr or "File scanner rejected the upload").strip()
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=f"File scan failed: {detail[:500]}")


def _scan_command(command: str, path: Path) -> list[str]:
    parts = shlex.split(command, posix=os.name != "nt")
    if "{path}" in command:
        return [str(path) if part.strip("\"'") == "{path}" else part for part in parts]
    return [*parts, str(path)]


def persist_pdf_upload(file: UploadFile, target: Path, max_upload_mb: int) -> str:
    checksum, document_type = persist_upload(file, target, max_upload_mb)
    if document_type != "pdf":
        target.unlink(missing_ok=True)
        raise HTTPException(status_code=400, detail="Only PDF uploads are supported")
    return checksum
