import re
import uuid

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.entities import EvaluationRecord, UsageRecord

CITATION_RE = re.compile(r"\[(\d+)\]")


def record_usage(
    db: Session,
    owner_id: uuid.UUID,
    operation: str,
    input_text: str,
    output_text: str,
    document_id: uuid.UUID | None = None,
) -> None:
    settings = get_settings()
    model = settings.openai_model if settings.llm_provider == "openai" else settings.ollama_model
    chars = len(input_text) + len(output_text)
    db.add(
        UsageRecord(
            owner_id=owner_id,
            document_id=document_id,
            operation=operation,
            provider=settings.llm_provider,
            model=model,
            input_chars=len(input_text),
            output_chars=len(output_text),
            estimated_tokens=max(1, chars // 4),
        )
    )


def record_answer_evaluation(
    db: Session,
    owner_id: uuid.UUID,
    question: str,
    answer: str,
    source_count: int,
    document_id: uuid.UUID | None = None,
) -> EvaluationRecord:
    cited = {int(match.group(1)) for match in CITATION_RE.finditer(answer)}
    valid = {index for index in cited if 1 <= index <= source_count}
    unsupported = cited - valid
    score = 0 if source_count == 0 else round((len(valid) / max(source_count, 1)) * 100)
    if unsupported:
        score = max(0, score - 25)
    evaluation = EvaluationRecord(
        owner_id=owner_id,
        document_id=document_id,
        question=question,
        answer=answer,
        source_count=source_count,
        cited_source_count=len(valid),
        unsupported_citation_count=len(unsupported),
        groundedness_score=score,
        notes="Automatic citation coverage check.",
    )
    db.add(evaluation)
    return evaluation
