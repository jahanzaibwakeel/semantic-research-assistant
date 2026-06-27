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
            raise RuntimeError("OCR fallback is enabled but no OCR engine is configured in this build")
        if total_chars < settings.ocr_min_text_chars:
            raise RuntimeError(
                "PDF text extraction produced very little text. This may be a scanned PDF; enable OCR support to process it."
            )
        return pages
    text = path.read_text(encoding="utf-8", errors="replace")
    return [LCDocument(page_content=text, metadata={"source": str(path), "page": None})]


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
