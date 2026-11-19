"""Optional Ragas metrics with a safe fallback.

The deterministic metrics remain the always-available regression signal. When
Ragas is installed and the configured LangChain model supports it, this module
adds judge-based metrics to the case without making evaluation unavailable in
offline/Ollama environments.
"""

from __future__ import annotations

import asyncio
from typing import Any


async def evaluate_with_ragas(
    *,
    question: str,
    answer: str,
    contexts: list[str],
    reference: str | None,
    model: Any,
) -> dict[str, float] | None:
    if not answer or not contexts or model is None:
        return None

    try:
        from ragas import EvaluationDataset, evaluate
        from ragas.dataset_schema import SingleTurnSample
        from ragas.llms import LangchainLLMWrapper
        from ragas.metrics import (
            ContextPrecision,
            ContextRecall,
            Faithfulness,
            ResponseRelevancy,
        )
    except (ImportError, ModuleNotFoundError):
        return None

    sample = SingleTurnSample(
        user_input=question,
        response=answer,
        retrieved_contexts=contexts,
        reference=reference,
    )

    def run() -> dict[str, float]:
        result = evaluate(
            dataset=EvaluationDataset(samples=[sample]),
            metrics=[
                Faithfulness(),
                ResponseRelevancy(),
                ContextPrecision(),
                ContextRecall(),
            ],
            llm=LangchainLLMWrapper(model),
        )
        values = result.to_pandas().iloc[0].to_dict()
        aliases = {
            "faithfulness": "faithfulness",
            "answer_relevance": "answer_relevancy",
            "context_precision": "context_precision",
            "context_recall": "context_recall",
        }
        return {
            target: float(values[source])
            for target, source in aliases.items()
            if values.get(source) is not None
        }

    try:
        return await asyncio.to_thread(run)
    except Exception:
        # A judge failure should not erase the deterministic evaluation.
        return None
