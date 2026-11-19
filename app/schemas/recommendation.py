from typing import Literal

from pydantic import BaseModel, Field


class RecommendationRequest(BaseModel):
    user_id: str = Field(
        default="demo-user",
        min_length=1,
        max_length=128,
    )

    limit: int = Field(
        default=5,
        ge=1,
        le=10,
    )

    include_seen: bool = False


class RecommendationItem(BaseModel):
    document_id: int
    filename: str
    score: float
    semantic_score: float
    behavioural_score: float
    popularity_score: float
    seen: bool
    reason: str
    preview: str
    chunk_count: int


class RecommendationResponse(BaseModel):
    user_id: str
    strategy: Literal[
        "personalised",
        "cold_start",
    ]
    interaction_count: int
    generated_at: str
    items: list[RecommendationItem]


class RecommendationFeedbackRequest(BaseModel):
    user_id: str = Field(
        default="demo-user",
        min_length=1,
        max_length=128,
    )

    document_id: int

    relevant: bool

    note: str | None = Field(
        default=None,
        max_length=500,
    )


class RecommendationEventRequest(BaseModel):
    user_id: str = Field(
        default="demo-user",
        min_length=1,
        max_length=128,
    )

    document_id: int

    event_type: Literal[
        "view",
        "open",
        "search",
    ] = "view"

    query: str | None = Field(
        default=None,
        max_length=500,
    )
