from typing import Any

from pydantic import BaseModel, Field


class EvaluationRequest(BaseModel):
    dataset: str = Field(
        default="demo_dataset",
        min_length=1,
        max_length=120,
    )

    pipelines: list[str] | None = None

    max_cases: int = Field(
        default=6,
        ge=1,
        le=10,
    )


class EvaluationCaseRead(BaseModel):
    id: int
    pipeline: str
    question: str
    expected_answer: str | None
    expected_document_ids: list[int] | None
    answer: str | None
    retrieved_document_ids: list[int] | None
    metrics: dict[str, Any] | None
    latency_ms: int
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    passed: bool
    error: str | None


class EvaluationRunRead(BaseModel):
    id: int
    dataset: str
    status: str
    case_count: int
    pipelines: list[dict] | None
    summary: dict[str, Any] | None
    error: str | None
    started_at: str
    completed_at: str | None


class EvaluationRunDetail(BaseModel):
    run: EvaluationRunRead
    cases: list[EvaluationCaseRead]
