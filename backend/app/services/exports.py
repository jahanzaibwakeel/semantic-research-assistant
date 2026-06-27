import re
import uuid
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.entities import Document, ResearchExtraction


def project_markdown_report(db: Session, owner_id: uuid.UUID, project_id: uuid.UUID | None = None) -> str:
    rows = _extraction_rows(db, owner_id, project_id)
    lines = ["# Semantic Research Report", ""]
    for document, extraction in rows:
        lines.extend(
            [
                f"## {extraction.title or document.title or document.filename}",
                "",
                f"**Authors:** {extraction.authors or 'Unknown'}",
                f"**Year:** {extraction.publication_year or 'Unknown'}",
                f"**Venue:** {extraction.venue or 'Unknown'}",
                f"**DOI:** {extraction.doi or 'Not found'}",
                "",
                "### Abstract",
                extraction.abstract or "Not extracted.",
                "",
                "### Methods",
                extraction.methods or "Not extracted.",
                "",
                "### Claims",
                extraction.claims or "Not extracted.",
                "",
                "### Findings",
                extraction.findings or "Not extracted.",
                "",
                "### Limitations",
                extraction.limitations or "Not extracted.",
                "",
                "### Annotated Bibliography",
                extraction.annotated_bibliography or "Not extracted.",
                "",
            ]
        )
    if len(lines) == 2:
        lines.append("No extracted research profiles are available yet.")
    return "\n".join(lines)


def project_bibtex(db: Session, owner_id: uuid.UUID, project_id: uuid.UUID | None = None) -> str:
    entries = []
    for document, extraction in _extraction_rows(db, owner_id, project_id):
        key = _bibtex_key(extraction, document)
        entries.append(
            "\n".join(
                [
                    f"@article{{{key},",
                    f"  title = {{{_clean_bib(extraction.title or document.title or document.filename)}}},",
                    f"  author = {{{_clean_bib(extraction.authors or 'Unknown')}}},",
                    f"  year = {{{_clean_bib(extraction.publication_year or 'n.d.')}}},",
                    f"  journal = {{{_clean_bib(extraction.venue or '')}}},",
                    f"  doi = {{{_clean_bib(extraction.doi or '')}}}",
                    "}",
                ]
            )
        )
    return "\n\n".join(entries) or "% No extracted research profiles are available yet."


def project_manifest_json(db: Session, owner_id: uuid.UUID, project_id: uuid.UUID | None = None) -> dict:
    rows = _extraction_rows(db, owner_id, project_id)
    return {
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "document_count": len(rows),
        "documents": [
            {
                "document_id": str(document.id),
                "filename": document.filename,
                "document_type": document.document_type,
                "source_url": document.source_url,
                "tags": document.tags,
                "status": document.status,
                "title": extraction.title or document.title,
                "authors": extraction.authors,
                "year": extraction.publication_year,
                "doi": extraction.doi,
                "methods": extraction.methods,
                "findings": extraction.findings,
                "limitations": extraction.limitations,
            }
            for document, extraction in rows
        ],
    }


def _extraction_rows(db: Session, owner_id: uuid.UUID, project_id: uuid.UUID | None):
    filters = [Document.owner_id == owner_id, Document.status != "deleted"]
    if project_id:
        filters.append(Document.project_id == project_id)
    return db.execute(
        select(Document, ResearchExtraction)
        .join(ResearchExtraction, ResearchExtraction.document_id == Document.id)
        .where(*filters)
        .order_by(Document.created_at.desc())
    ).all()


def _bibtex_key(extraction: ResearchExtraction, document: Document) -> str:
    author = (extraction.authors or "unknown").split(",")[0]
    year = extraction.publication_year or "nd"
    title = extraction.title or document.title or document.filename
    raw = f"{author}{year}{title.split()[0] if title.split() else 'paper'}"
    return re.sub(r"[^A-Za-z0-9_:-]", "", raw)[:60] or "paper"


def _clean_bib(value: str) -> str:
    return value.replace("{", "").replace("}", "").strip()
