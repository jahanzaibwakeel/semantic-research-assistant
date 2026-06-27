from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, EmailStr, field_validator


class RetrievalOptions(BaseModel):
    mode: str = "hybrid"
    rewrite_query: bool = True
    min_score: float | None = None

    @field_validator("mode")
    @classmethod
    def validate_mode(cls, value: str) -> str:
        normalized = value.lower().strip()
        if normalized not in {"hybrid", "vector", "keyword"}:
            raise ValueError("mode must be one of: hybrid, vector, keyword")
        return normalized


class UserCreate(BaseModel):
    email: EmailStr
    password: str
    full_name: str | None = None


class UserRead(BaseModel):
    id: uuid.UUID
    email: EmailStr
    full_name: str | None = None

    model_config = {"from_attributes": True}


class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: UserRead


class RefreshTokenRequest(BaseModel):
    refresh_token: str


class LogoutRequest(BaseModel):
    refresh_token: str | None = None


class PasswordChangeRequest(BaseModel):
    current_password: str
    new_password: str


class ApiKeyCreate(BaseModel):
    name: str


class ApiKeyRead(BaseModel):
    id: uuid.UUID
    name: str
    key_prefix: str
    revoked: bool
    last_used_at: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}


class ApiKeyCreated(ApiKeyRead):
    api_key: str


class DocumentRead(BaseModel):
    id: uuid.UUID
    project_id: uuid.UUID | None
    filename: str
    document_type: str
    source_url: str | None
    checksum: str | None
    title: str | None
    tags: str | None
    status: str
    page_count: int
    chunk_count: int
    summary: str | None
    key_points: str | None
    error_message: str | None
    processed_at: datetime | None
    indexed_at: datetime | None
    deleted_at: datetime | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class DocumentUpdate(BaseModel):
    title: str | None = None
    tags: str | None = None
    project_id: uuid.UUID | None = None


class ProjectCreate(BaseModel):
    name: str
    description: str | None = None


class ProjectRead(BaseModel):
    id: uuid.UUID
    name: str
    description: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class SavedQueryCreate(BaseModel):
    title: str
    query: str
    mode: str = "hybrid"
    project_id: uuid.UUID | None = None


class SavedQueryRead(BaseModel):
    id: uuid.UUID
    title: str
    query: str
    mode: str
    project_id: uuid.UUID | None
    created_at: datetime

    model_config = {"from_attributes": True}


class ResearchNoteCreate(BaseModel):
    title: str
    body: str
    project_id: uuid.UUID | None = None
    document_id: uuid.UUID | None = None
    pinned: bool = False


class ResearchNoteRead(BaseModel):
    id: uuid.UUID
    title: str
    body: str
    project_id: uuid.UUID | None
    document_id: uuid.UUID | None
    pinned: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ResearchExtractionRead(BaseModel):
    id: uuid.UUID
    document_id: uuid.UUID
    title: str | None
    authors: str | None
    publication_year: str | None
    venue: str | None
    doi: str | None
    abstract: str | None
    research_question: str | None
    methods: str | None
    datasets: str | None
    claims: str | None
    evidence: str | None
    findings: str | None
    limitations: str | None
    future_work: str | None
    practical_implications: str | None
    annotated_bibliography: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class LiteratureMatrixRow(BaseModel):
    document_id: uuid.UUID
    filename: str
    title: str | None
    authors: str | None
    year: str | None
    methods: str | None
    datasets: str | None
    claims: str | None
    findings: str | None
    limitations: str | None


class ResearchSynthesisRequest(BaseModel):
    focus: str = "Compare the papers by research question, methods, findings, and limitations."


class SourceCitation(BaseModel):
    document_id: uuid.UUID
    filename: str
    page: int | None = None
    chunk_index: int | None = None
    score: float | None = None
    vector_score: float | None = None
    keyword_score: float | None = None
    retrieval_method: str = "hybrid"
    excerpt: str


class SearchRequest(RetrievalOptions):
    query: str
    document_id: uuid.UUID | None = None
    project_id: uuid.UUID | None = None
    document_type: str | None = None
    tags: str | None = None
    limit: int = 8
    include_rewritten_query: bool = True


class SearchResponse(BaseModel):
    results: list[SourceCitation]
    rewritten_query: str | None = None


class QuestionRequest(RetrievalOptions):
    question: str
    document_id: uuid.UUID | None = None
    project_id: uuid.UUID | None = None
    document_type: str | None = None
    tags: str | None = None
    limit: int = 8


class AnswerResponse(BaseModel):
    answer: str
    sources: list[SourceCitation]
    rewritten_query: str | None = None


class CompareRequest(BaseModel):
    left_document_id: uuid.UUID
    right_document_id: uuid.UUID
    focus: str | None = "claims, methods, limitations, and findings"


class BulkDocumentAction(BaseModel):
    document_ids: list[uuid.UUID]


class UrlIngestRequest(BaseModel):
    url: str
    title: str | None = None
    project_id: uuid.UUID | None = None
    tags: str | None = None


class ResearchSynthesisResponse(BaseModel):
    synthesis: str
    sources: list[SourceCitation] = []


class UsageSummary(BaseModel):
    operation: str
    calls: int
    estimated_tokens: int


class OperationalStatus(BaseModel):
    documents_by_status: dict[str, int]
    documents_by_type: dict[str, int]
    recent_failures: list[DocumentRead]


class EvaluationRead(BaseModel):
    id: uuid.UUID
    document_id: uuid.UUID | None
    question: str
    source_count: int
    cited_source_count: int
    unsupported_citation_count: int
    groundedness_score: int
    notes: str | None
    created_at: datetime

    model_config = {"from_attributes": True}
