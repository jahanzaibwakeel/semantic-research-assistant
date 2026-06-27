import hashlib
from pathlib import Path

from fastapi import HTTPException, UploadFile, status

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


def persist_pdf_upload(file: UploadFile, target: Path, max_upload_mb: int) -> str:
    checksum, document_type = persist_upload(file, target, max_upload_mb)
    if document_type != "pdf":
        target.unlink(missing_ok=True)
        raise HTTPException(status_code=400, detail="Only PDF uploads are supported")
    return checksum
