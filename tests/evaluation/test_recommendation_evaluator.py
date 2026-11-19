import json
from pathlib import Path

import pytest

from app.evaluation.recommendation_evaluator import (
    RecommendationCase,
    evaluate_recommendations,
)


def test_recommendation_benchmark_has_useful_top_five_results():
    path = Path(__file__).parent / "data" / "recommendation_dataset.json"
    cases = [
        RecommendationCase(
            user_id=item["user_id"],
            recommended_document_ids=item["recommended_document_ids"],
            relevant_document_ids=set(item["relevant_document_ids"]),
        )
        for item in json.loads(path.read_text(encoding="utf-8"))
    ]

    result = evaluate_recommendations(cases, k=5)

    assert result.users == 4
    assert result.precision_at_k == pytest.approx(0.65)
    assert result.recall_at_k == pytest.approx(0.9167, abs=0.0001)
    assert result.hit_rate_at_k == 1.0


def test_recommendation_benchmark_requires_cases():
    with pytest.raises(ValueError):
        evaluate_recommendations([])
