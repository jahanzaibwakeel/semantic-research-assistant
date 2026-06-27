import json
import re
import uuid

from langchain_core.prompts import ChatPromptTemplate
from sqlalchemy.orm import Session

from app.models.entities import Document, InteractionHistory
from app.schemas.dto import SourceCitation
from app.services.ai import get_llm
from app.services.retrieval import RetrievedChunk, retrieve_chunks, rewrite_query
from app.services.usage import record_answer_evaluation, record_usage

CITATION_RE = re.compile(r"\[(\d+)\]")


def _citations(results: list[RetrievedChunk]) -> list[SourceCitation]:
    citations: list[SourceCitation] = []
    for item in results:
        citations.append(
            SourceCitation(
                document_id=item.document_id,
                filename=item.filename,
                page=item.page,
                chunk_index=item.chunk_index,
                score=item.score,
                vector_score=item.vector_score,
                keyword_score=item.keyword_score,
                retrieval_method=item.retrieval_method,
                excerpt=item.text[:700],
            )
        )
    return citations


def semantic_search(
    db: Session,
    owner_id: uuid.UUID,
    query: str,
    document_id: uuid.UUID | None,
    limit: int,
    mode: str = "hybrid",
    rewrite: bool = True,
    min_score: float | None = None,
    project_id: uuid.UUID | None = None,
    document_type: str | None = None,
    tags: str | None = None,
):
    retrieval_query = rewrite_query(query) if rewrite else query
    results = retrieve_chunks(
        query=retrieval_query,
        owner_id=owner_id,
        document_id=document_id,
        project_id=project_id,
        document_type=document_type,
        tags=tags,
        limit=limit,
        mode=mode,
        min_score=min_score,
    )
    citations = _citations(results)
    db.add(
        InteractionHistory(
            owner_id=owner_id,
            kind="search",
            query=json.dumps({"query": query, "retrieval_query": retrieval_query, "mode": mode}),
            response=json.dumps([citation.model_dump(mode="json") for citation in citations]),
            document_id=document_id,
        )
    )
    db.commit()
    return citations, retrieval_query


def answer_question(
    db: Session,
    owner_id: uuid.UUID,
    question: str,
    document_id: uuid.UUID | None,
    limit: int,
    mode: str = "hybrid",
    rewrite: bool = True,
    min_score: float | None = None,
    project_id: uuid.UUID | None = None,
    document_type: str | None = None,
    tags: str | None = None,
):
    retrieval_query = rewrite_query(question) if rewrite else question
    results = retrieve_chunks(
        query=retrieval_query,
        owner_id=owner_id,
        document_id=document_id,
        project_id=project_id,
        document_type=document_type,
        tags=tags,
        limit=limit,
        mode=mode,
        min_score=min_score,
    )
    citations = _citations(results)
    if not citations:
        answer = "I could not find enough relevant context in the indexed documents to answer that confidently."
        _record_history(db, owner_id, "qa", question, answer, document_id)
        return answer, citations, retrieval_query

    context = "\n\n".join(
        f"[{index + 1}] {citation.filename}, page {citation.page}: {citation.excerpt}"
        for index, citation in enumerate(citations)
    )
    prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                "You are a precise research assistant. Answer only from the supplied context. "
                "Every factual claim must include one or more inline citations like [1] or [2]. "
                "Use only citation numbers that exist in the supplied context. "
                "If the context is insufficient, say what is missing and cite the closest available context.",
            ),
            ("human", "Question: {question}\n\nContext:\n{context}"),
        ]
    )
    answer = (prompt | get_llm()).invoke({"question": question, "context": context}).content
    answer = _enforce_citations(answer, len(citations))
    record_usage(db, owner_id, "qa", f"{question}\n\n{context}", answer, document_id)
    record_answer_evaluation(db, owner_id, question, answer, len(citations), document_id)
    _record_history(db, owner_id, "qa", json.dumps({"question": question, "retrieval_query": retrieval_query, "mode": mode}), answer, document_id)
    return answer, citations, retrieval_query


def retrieve_question_context(
    owner_id: uuid.UUID,
    question: str,
    document_id: uuid.UUID | None,
    limit: int,
    mode: str = "hybrid",
    rewrite: bool = True,
    min_score: float | None = None,
    project_id: uuid.UUID | None = None,
    document_type: str | None = None,
    tags: str | None = None,
):
    retrieval_query = rewrite_query(question) if rewrite else question
    results = retrieve_chunks(
        query=retrieval_query,
        owner_id=owner_id,
        document_id=document_id,
        project_id=project_id,
        document_type=document_type,
        tags=tags,
        limit=limit,
        mode=mode,
        min_score=min_score,
    )
    citations = _citations(results)
    context = "\n\n".join(
        f"[{index + 1}] {citation.filename}, page {citation.page}: {citation.excerpt}"
        for index, citation in enumerate(citations)
    )
    return retrieval_query, citations, context


def summarize_document(db: Session, owner_id: uuid.UUID, document: Document) -> tuple[str, str]:
    question = (
        "Create a concise research summary and extract key points, claims, methods, limitations, "
        "and findings from this document."
    )
    answer, _, _ = answer_question(db, owner_id, question, document.id, limit=14, mode="hybrid", rewrite=False)
    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", "Convert the analysis into two sections: Summary and Key Points. Keep it factual."),
            ("human", "{analysis}"),
        ]
    )
    formatted = (prompt | get_llm()).invoke({"analysis": answer}).content
    record_usage(db, owner_id, "summary_format", answer, formatted, document.id)
    return formatted, answer


def compare_documents(db: Session, owner_id: uuid.UUID, left: Document, right: Document, focus: str):
    retrieval_query = rewrite_query(focus)
    left_results = retrieve_chunks(retrieval_query, owner_id, left.id, limit=8, mode="hybrid")
    right_results = retrieve_chunks(retrieval_query, owner_id, right.id, limit=8, mode="hybrid")
    citations = _citations(left_results) + _citations(right_results)
    if not citations:
        answer = "I could not find enough relevant context in either document to compare them confidently."
        _record_history(db, owner_id, "compare", focus, answer, None)
        return answer, citations, retrieval_query

    context = "\n\n".join(
        f"[{index + 1}] {citation.filename}, page {citation.page}: {citation.excerpt}"
        for index, citation in enumerate(citations)
    )
    prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                "Compare the two documents as a research analyst. Contrast thesis, methods, evidence, "
                "findings, limitations, and practical implications. Cite context as [1], [2].",
            ),
            ("human", "Comparison focus: {focus}\n\nContext:\n{context}"),
        ]
    )
    answer = (prompt | get_llm()).invoke({"focus": focus, "context": context}).content
    answer = _enforce_citations(answer, len(citations))
    record_usage(db, owner_id, "compare", f"{focus}\n\n{context}", answer)
    record_answer_evaluation(db, owner_id, focus, answer, len(citations))
    _record_history(db, owner_id, "compare", json.dumps({"focus": focus, "retrieval_query": retrieval_query}), answer, None)
    return answer, citations, retrieval_query


def _enforce_citations(answer: str, source_count: int) -> str:
    cited = {int(match.group(1)) for match in CITATION_RE.finditer(answer)}
    valid = {index for index in cited if 1 <= index <= source_count}
    if not valid and source_count > 0:
        return f"{answer.rstrip()}\n\nSources: [1]"
    invalid = cited - valid
    if invalid:
        answer = f"{answer.rstrip()}\n\nNote: Removed unsupported citation references outside the retrieved source range."
    return answer


def _record_history(
    db: Session,
    owner_id: uuid.UUID,
    kind: str,
    query: str,
    response: str,
    document_id: uuid.UUID | None,
) -> None:
    db.add(
        InteractionHistory(
            owner_id=owner_id,
            kind=kind,
            query=query,
            response=response,
            document_id=document_id,
        )
    )
    db.commit()
