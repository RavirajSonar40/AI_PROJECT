from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator


class PlanRequest(BaseModel):
    task: str = Field(
        min_length=5,
        max_length=2000,
    )

    user_id: str = Field(
        default="demo-user",
        min_length=1,
        max_length=128,
    )

    thread_id: str | None = Field(
        default=None,
        min_length=1,
        max_length=128,
    )

    limit: int = Field(
        default=5,
        ge=1,
        le=10,
    )

    min_similarity: float = Field(
        default=0.2,
        ge=0.0,
        le=1.0,
    )

    max_revisions: int = Field(
        default=1,
        ge=0,
        le=3,
    )

    @field_validator("task")
    @classmethod
    def validate_task(
        cls,
        value: str,
    ) -> str:
        normalized = value.strip()

        if len(normalized) < 5:
            raise ValueError(
                "The task must contain at least "
                "5 characters."
            )

        return normalized


class PlanResumeRequest(BaseModel):
    thread_id: str = Field(
        min_length=1,
        max_length=128,
    )

    approved: bool

    note: str | None = Field(
        default=None,
        max_length=500,
    )


class PlanStepRead(BaseModel):
    id: int
    title: str
    action: Literal[
        "search_knowledge",
        "analyze",
        "draft",
    ]
    query: str = ""
    status: str | None = None
    evidence_count: int = 0


class PlanEvidenceRead(BaseModel):
    step_id: int
    document_id: int
    position: int
    similarity: float
    content: str


class PlanResponse(BaseModel):
    thread_id: str

    status: Literal[
        "completed",
        "interrupted",
        "rejected",
    ]

    task: str

    plan_summary: str = ""

    plan_steps: list[PlanStepRead] = Field(
        default_factory=list
    )

    dependencies: list[str] = Field(
        default_factory=list
    )

    risks: list[str] = Field(
        default_factory=list
    )

    evidence: list[PlanEvidenceRead] = Field(
        default_factory=list
    )

    draft: str | None = None

    critique: str | None = None

    issues: list[str] = Field(
        default_factory=list
    )

    confidence: float | None = None

    verification_passed: bool | None = None

    revision_count: int = 0

    answer: str | None = None

    approval: dict[str, Any] | None = None

    interrupt: dict[str, Any] | None = None
