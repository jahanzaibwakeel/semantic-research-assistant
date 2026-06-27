import re
import uuid
from dataclasses import dataclass

from langchain_core.prompts import ChatPromptTemplate

from app.core.config import get_settings
from app.services.ai import get_llm
from app.services.qdrant_store import QdrantStore

TOKEN_RE = re.compile(r"[a-zA-Z0-9][a-zA-Z0-9_-]{2,}")


@dataclass
class RetrievedChunk:
    document_id: uuid.UUID
    filename: str
    text: str
    page: int | None
    chunk_index: int | None
    score: float
    vector_score: float | None = None
    keyword_score: float | None = None
    retrieval_method: str = "hybrid"

    @property
    def key(self) -> str:
        return f"{self.document_id}:{self.chunk_index}"


def rewrite_query(question: str) -> str:
    prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                "Rewrite the user question as a concise retrieval query. Keep domain terms, acronyms, "
                "authors, methods, datasets, and quoted phrases. Return only the query.",
            ),
            ("human", "{question}"),
        ]
    )
    try:
        rewritten = (prompt | get_llm()).invoke({"question": question}).content.strip()
    except Exception:
        return question
    return rewritten or question


def retrieve_chunks(
    query: str,
    owner_id: uuid.UUID,
    document_id: uuid.UUID | None = None,
    project_id: uuid.UUID | None = None,
    document_type: str | None = None,
    tags: str | None = None,
    limit: int = 8,
    mode: str = "hybrid",
    min_score: float | None = None,
) -> list[RetrievedChunk]:
    settings = get_settings()
    store = QdrantStore()
    normalized_mode = mode.lower().strip()
    threshold = settings.min_relevance_score if min_score is None else min_score
    candidates: dict[str, RetrievedChunk] = {}

    if normalized_mode in {"vector", "hybrid"}:
        vector_limit = max(limit, limit * settings.vector_candidate_multiplier)
        for item in store.search(
            query=query,
            owner_id=owner_id,
            document_id=document_id,
            project_id=project_id,
            document_type=document_type,
            limit=vector_limit,
        ):
            if not _matches_tags(item.payload or {}, tags):
                continue
            chunk = _chunk_from_payload(item.payload or {}, vector_score=float(item.score), method="vector")
            if chunk:
                candidates[chunk.key] = chunk

    if normalized_mode in {"keyword", "hybrid"}:
        keyword_chunks = _keyword_search(
            store=store,
            query=query,
            owner_id=owner_id,
            document_id=document_id,
            project_id=project_id,
            document_type=document_type,
            tags=tags,
            limit=settings.keyword_candidate_limit,
        )
        for chunk in keyword_chunks:
            existing = candidates.get(chunk.key)
            if existing:
                existing.keyword_score = chunk.keyword_score
                existing.score = _fuse_scores(existing.vector_score, chunk.keyword_score)
                existing.retrieval_method = "hybrid"
            else:
                candidates[chunk.key] = chunk

    ranked = sorted(
        (_rerank(query, chunk) for chunk in candidates.values()),
        key=lambda chunk: chunk.score,
        reverse=True,
    )
    return [chunk for chunk in ranked if chunk.score >= threshold][:limit]


def _keyword_search(
    store: QdrantStore,
    query: str,
    owner_id: uuid.UUID,
    document_id: uuid.UUID | None,
    project_id: uuid.UUID | None,
    document_type: str | None,
    tags: str | None,
    limit: int,
) -> list[RetrievedChunk]:
    chunks: list[RetrievedChunk] = []
    for point in store.scroll_payloads(
        owner_id=owner_id,
        document_id=document_id,
        project_id=project_id,
        document_type=document_type,
        limit=limit,
    ):
        payload = point.payload or {}
        if not _matches_tags(payload, tags):
            continue
        keyword_score = _keyword_score(query, payload.get("text", ""))
        if keyword_score <= 0:
            continue
        chunk = _chunk_from_payload(payload, keyword_score=keyword_score, method="keyword")
        if chunk:
            chunks.append(chunk)
    return sorted(chunks, key=lambda chunk: chunk.score, reverse=True)


def _chunk_from_payload(
    payload: dict,
    vector_score: float | None = None,
    keyword_score: float | None = None,
    method: str = "hybrid",
) -> RetrievedChunk | None:
    document_id = payload.get("document_id")
    text = payload.get("text", "")
    if not document_id or not text:
        return None
    fused = _fuse_scores(vector_score, keyword_score)
    return RetrievedChunk(
        document_id=uuid.UUID(document_id),
        filename=payload.get("filename", "document"),
        text=text,
        page=payload.get("page"),
        chunk_index=payload.get("chunk_index"),
        score=fused,
        vector_score=vector_score,
        keyword_score=keyword_score,
        retrieval_method=method,
    )


def _rerank(query: str, chunk: RetrievedChunk) -> RetrievedChunk:
    lexical_boost = _keyword_score(query, chunk.text) * 0.15
    chunk.score = min(1.0, chunk.score + lexical_boost)
    return chunk


def _fuse_scores(vector_score: float | None, keyword_score: float | None) -> float:
    if vector_score is not None and keyword_score is not None:
        return (0.72 * vector_score) + (0.28 * keyword_score)
    if vector_score is not None:
        return vector_score
    return keyword_score or 0.0


def _keyword_score(query: str, text: str) -> float:
    query_terms = _terms(query)
    if not query_terms:
        return 0.0
    text_terms = _terms(text)
    if not text_terms:
        return 0.0
    unique_query_terms = set(query_terms)
    matched = sum(1 for term in unique_query_terms if term in text_terms)
    density = min(1.0, sum(text_terms.count(term) for term in unique_query_terms) / max(len(query_terms), 1))
    coverage = matched / len(unique_query_terms)
    return min(1.0, (0.75 * coverage) + (0.25 * density))


def _terms(value: str) -> list[str]:
    return [match.group(0).lower() for match in TOKEN_RE.finditer(value)]


def _matches_tags(payload: dict, tags: str | None) -> bool:
    if not tags:
        return True
    requested = {tag.strip().lower() for tag in tags.split(",") if tag.strip()}
    if not requested:
        return True
    payload_tags = {tag.strip().lower() for tag in str(payload.get("tags") or "").split(",") if tag.strip()}
    return requested.issubset(payload_tags)
