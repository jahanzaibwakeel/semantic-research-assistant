import json
import uuid

from langchain_core.prompts import ChatPromptTemplate
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.tracing import traced_span
from app.models.entities import Document, ResearchExtraction
from app.services.ai import get_llm
from app.services.rag import answer_question
from app.services.usage import record_usage

EXTRACTION_FIELDS = {
    "title": "Extract the paper title. Return only the title if available.",
    "authors": "Extract author names. Return a comma-separated list if available.",
    "publication_year": "Extract the publication year if available.",
    "venue": "Extract the journal, conference, venue, or publisher if available.",
    "doi": "Extract the DOI if available.",
    "abstract": "Extract or reconstruct a concise abstract from the document.",
    "research_question": "Identify the main research question or objective.",
    "methods": "Extract the methods, approach, experimental setup, or analytical framework.",
    "datasets": "Extract datasets, corpora, samples, participants, benchmarks, or source material used.",
    "claims": "List the central claims made by the authors.",
    "evidence": "List the main evidence supporting the claims.",
    "findings": "List the main findings or results.",
    "limitations": "List limitations, threats to validity, caveats, or constraints.",
    "future_work": "Extract future work or open questions.",
    "practical_implications": "Extract practical implications or applications.",
}


def extract_research_profile(db: Session, owner_id: uuid.UUID, document: Document) -> ResearchExtraction:
    extraction = db.scalar(select(ResearchExtraction).where(ResearchExtraction.document_id == document.id))
    if not extraction:
        extraction = ResearchExtraction(document_id=document.id, owner_id=owner_id)
        db.add(extraction)

    for field, question in EXTRACTION_FIELDS.items():
        answer, _, _ = answer_question(
            db,
            owner_id,
            question,
            document.id,
            limit=10,
            mode="hybrid",
            rewrite=False,
            min_score=0.0,
        )
        setattr(extraction, field, _clean_answer(answer))

    extraction.annotated_bibliography = create_annotated_bibliography(extraction)
    db.commit()
    db.refresh(extraction)
    return extraction


def create_annotated_bibliography(extraction: ResearchExtraction) -> str:
    title = extraction.title or "Untitled document"
    authors = extraction.authors or "Unknown authors"
    year = f" ({extraction.publication_year})" if extraction.publication_year else ""
    findings = extraction.findings or "Main findings were not confidently extracted."
    limitations = extraction.limitations or "Limitations were not confidently extracted."
    return f"{authors}{year}. {title}. Findings: {findings} Limitations: {limitations}"


def synthesize_literature(db: Session, owner_id: uuid.UUID, focus: str) -> str:
    rows = db.scalars(
        select(ResearchExtraction)
        .join(Document, ResearchExtraction.document_id == Document.id)
        .where(ResearchExtraction.owner_id == owner_id, Document.status != "deleted")
        .order_by(ResearchExtraction.updated_at.desc())
    ).all()
    matrix = [
        {
            "title": row.title,
            "authors": row.authors,
            "year": row.publication_year,
            "methods": row.methods,
            "claims": row.claims,
            "findings": row.findings,
            "limitations": row.limitations,
        }
        for row in rows
    ]
    if not matrix:
        return "No extracted research profiles are available yet."

    prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                "You synthesize literature matrices. Compare patterns, agreements, disagreements, "
                "methodological differences, evidence gaps, and limitations. Be concise and concrete.",
            ),
            ("human", "Focus: {focus}\n\nLiterature matrix JSON:\n{matrix}"),
        ]
    )
    matrix_json = json.dumps(matrix, ensure_ascii=True)
    with traced_span("llm.synthesize_literature", matrix_rows=len(rows), focus_length=len(focus)):
        synthesis = (prompt | get_llm()).invoke({"focus": focus, "matrix": matrix_json}).content
    record_usage(db, owner_id, "literature_synthesis", f"{focus}\n\n{matrix_json}", synthesis)
    db.commit()
    return synthesis


def _clean_answer(answer: str) -> str:
    cleaned = answer.strip()
    if cleaned.lower().startswith("i could not find enough relevant context"):
        return ""
    return cleaned
