"""Offline evaluation for personalised recommendation rankings."""

from dataclasses import dataclass
from statistics import mean

from app.evaluation.retrieval_metrics import (
    hit_rate_at_k,
    precision_at_k,
    recall_at_k,
)


@dataclass(frozen=True)
class RecommendationCase:
    user_id: str
    recommended_document_ids: list[int]
    relevant_document_ids: set[int]


@dataclass(frozen=True)
class RecommendationEvaluation:
    k: int
    users: int
    precision_at_k: float
    recall_at_k: float
    hit_rate_at_k: float


def evaluate_recommendations(
    cases: list[RecommendationCase],
    k: int = 5,
) -> RecommendationEvaluation:
    if not cases:
        raise ValueError("At least one recommendation case is required.")

    metrics = [
        (
            precision_at_k(case.recommended_document_ids, case.relevant_document_ids, k),
            recall_at_k(case.recommended_document_ids, case.relevant_document_ids, k),
            hit_rate_at_k(case.recommended_document_ids, case.relevant_document_ids, k),
        )
        for case in cases
    ]

    return RecommendationEvaluation(
        k=k,
        users=len(cases),
        precision_at_k=round(mean(item[0] for item in metrics), 4),
        recall_at_k=round(mean(item[1] for item in metrics), 4),
        hit_rate_at_k=round(mean(item[2] for item in metrics), 4),
    )
