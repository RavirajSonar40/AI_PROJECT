"""Run the evaluation suite over several RAG configurations.

A run is synchronous and intentionally small: the goal is a reproducible
comparison on the demo corpus, not a benchmark harness. Each case is stored
so the dashboard can drill into failures.
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from statistics import mean

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.metrics import EVALUATION_RUNS
from app.evaluation.answer_metrics import (
    abstained,
    context_precision,
    context_recall,
    cosine_similarity,
    did_pass,
    lexical_faithfulness,
)
from app.evaluation.ragas_metrics import evaluate_with_ragas
from app.repositories.document_chunk import (
    DocumentChunkRepository,
)
from app.repositories.evaluation import (
    EvaluationRepository,
)
from app.services.chat_model_provider import (
    ChatModelProvider,
)
from app.services.embedding_service import (
    generate_embeddings,
)
from app.services.rag_service import RAGService
from app.services.token_usage import (
    estimate_prompt_tokens,
    estimate_tokens,
)

DATASETS_DIR = Path(__file__).parent / "datasets"

PIPELINES = {
    "baseline": {
        "name": "baseline",
        "label": (
            "Baseline - top-5, no similarity "
            "threshold"
        ),
        "limit": 5,
        "min_similarity": 0.0,
    },
    "enhanced": {
        "name": "enhanced",
        "label": (
            "Enhanced - top-3 above a 0.25 "
            "similarity threshold"
        ),
        "limit": 3,
        "min_similarity": 0.25,
    },
}

METRIC_KEYS = (
    "faithfulness",
    "answer_relevance",
    "context_precision",
    "context_recall",
)


def list_datasets() -> list[dict]:
    datasets = []

    for path in sorted(
        DATASETS_DIR.glob("*.json")
    ):
        try:
            cases = json.loads(
                path.read_text(
                    encoding="utf-8"
                )
            )

        except (
            OSError,
            json.JSONDecodeError,
        ):
            continue

        datasets.append(
            {
                "name": path.stem,
                "case_count": len(cases),
                "categories": sorted(
                    {
                        case.get(
                            "category",
                            "general",
                        )
                        for case in cases
                    }
                ),
            }
        )

    return datasets


def load_dataset(
    name: str = "demo_dataset",
) -> list[dict]:
    path = DATASETS_DIR / f"{name}.json"

    if not path.exists():
        raise ValueError(
            f"Unknown dataset: {name}"
        )

    return json.loads(
        path.read_text(encoding="utf-8")
    )


def resolve_pipelines(
    names: list[str] | None,
) -> list[dict]:
    selected = names or [
        "baseline",
        "enhanced",
    ]

    pipelines = []

    for name in selected:
        if name not in PIPELINES:
            raise ValueError(
                f"Unknown pipeline: {name}"
            )

        pipelines.append(PIPELINES[name])

    return pipelines


async def run_evaluation(
    session: AsyncSession,
    dataset_name: str = "demo_dataset",
    pipeline_names: list[str] | None = None,
    max_cases: int = 6,
) -> dict:
    cases = load_dataset(dataset_name)[
        : max(1, max_cases)
    ]

    pipelines = resolve_pipelines(
        pipeline_names
    )

    repository = EvaluationRepository(session)

    run = await repository.create_run(
        dataset=dataset_name,
        pipelines=pipelines,
        case_count=len(cases),
    )

    service = RAGService(
        chunk_retriever=DocumentChunkRepository(
            session
        ),
        llm=ChatModelProvider(),
    )

    rows: list[dict] = []

    try:
        for pipeline in pipelines:
            for case in cases:
                row = await _evaluate_case(
                    repository=repository,
                    run_id=run.id,
                    pipeline=pipeline,
                    case=case,
                    service=service,
                )

                rows.append(row)

        summary = _summarise(
            dataset=dataset_name,
            cases=cases,
            pipelines=pipelines,
            rows=rows,
        )

        await repository.complete_run(
            run.id,
            summary,
        )

        EVALUATION_RUNS.labels(
            status="completed"
        ).inc()

        return {
            "run_id": run.id,
            "dataset": dataset_name,
            "status": "completed",
            "case_count": len(cases),
            "summary": summary,
        }

    except Exception as exc:
        await repository.fail_run(
            run.id,
            str(exc),
        )

        EVALUATION_RUNS.labels(
            status="failed"
        ).inc()

        raise


async def _evaluate_case(
    repository: EvaluationRepository,
    run_id: int,
    pipeline: dict,
    case: dict,
    service: RAGService,
) -> dict:
    question = case["question"]
    expected_document_ids = [
        int(value)
        for value in case.get(
            "expected_document_ids",
            [],
        )
    ]

    started = time.perf_counter()

    answer = ""
    retrieved_document_ids: list[int] = []
    context = ""
    error: str | None = None

    try:
        answer, matches = await service.answer(
            question=question,
            limit=pipeline["limit"],
            min_similarity=(
                pipeline["min_similarity"]
            ),
        )

        retrieved_document_ids = sorted(
            {
                chunk.document_id
                for chunk, _ in matches
            }
        )

        context = "\n\n".join(
            chunk.content
            for chunk, _ in matches
        )

    except Exception as exc:
        error = str(exc)

    latency_ms = int(
        (time.perf_counter() - started)
        * 1000
    )

    did_abstain = abstained(answer)

    faithfulness = lexical_faithfulness(
        answer,
        context,
    )

    precision = context_precision(
        retrieved_document_ids,
        expected_document_ids,
    )

    recall = context_recall(
        retrieved_document_ids,
        expected_document_ids,
        did_abstain,
    )

    relevance = await _answer_relevance(
        question,
        answer,
    )

    passed = did_pass(
        expected_document_ids,
        did_abstain,
        faithfulness,
        recall,
    )

    if error:
        passed = False

    metrics = {
        "faithfulness": round(
            faithfulness,
            4,
        ),
        "answer_relevance": round(
            relevance,
            4,
        ),
        "context_precision": round(
            precision,
            4,
        ),
        "context_recall": round(
            recall,
            4,
        ),
        "abstained": did_abstain,
        "abstention_correct": (
            did_abstain
            if not expected_document_ids
            else None
        ),
        "retrieved_chunks": len(
            retrieved_document_ids
        ),
    }

    ragas_scores = await evaluate_with_ragas(
        question=question,
        answer=answer,
        contexts=[chunk.content for chunk, _ in matches],
        reference=case.get("expected_answer"),
        model=getattr(service.llm, "_model", None),
    )

    if ragas_scores:
        metrics.update(
            {
                f"ragas_{key}": round(value, 4)
                for key, value in ragas_scores.items()
            }
        )

    prompt_tokens = estimate_prompt_tokens(
        question,
        context,
    )

    completion_tokens = estimate_tokens(
        answer
    )

    provider_usage = getattr(
        service.llm,
        "last_usage",
        None,
    )

    if provider_usage is not None:
        prompt_tokens = provider_usage.prompt_tokens
        completion_tokens = provider_usage.completion_tokens
        metrics["usage_source"] = provider_usage.source
    else:
        metrics["usage_source"] = "estimated"

    await repository.add_case(
        run_id=run_id,
        pipeline=pipeline["name"],
        question=question,
        expected_answer=case.get(
            "expected_answer"
        ),
        expected_document_ids=(
            expected_document_ids
        ),
        answer=answer,
        retrieved_document_ids=(
            retrieved_document_ids
        ),
        metrics=metrics,
        latency_ms=latency_ms,
        prompt_tokens=prompt_tokens,
        completion_tokens=(
            completion_tokens
        ),
        passed=passed,
        error=error,
    )

    return {
        "pipeline": pipeline["name"],
        "category": case.get(
            "category",
            "general",
        ),
        "expected_document_ids": (
            expected_document_ids
        ),
        "retrieved_document_ids": (
            retrieved_document_ids
        ),
        "metrics": metrics,
        "passed": passed,
        "latency_ms": latency_ms,
        "total_tokens": (
            prompt_tokens
            + completion_tokens
        ),
        "error": error,
    }


async def _answer_relevance(
    question: str,
    answer: str,
) -> float:
    if not answer:
        return 0.0

    try:
        vectors = await generate_embeddings(
            [question, answer]
        )

    except Exception:
        return 0.0

    similarity = cosine_similarity(
        vectors[0],
        vectors[1],
    )

    return max(0.0, min(1.0, similarity))


def _summarise(
    dataset: str,
    cases: list[dict],
    pipelines: list[dict],
    rows: list[dict],
) -> dict:
    summaries = []

    for pipeline in pipelines:
        pipeline_rows = [
            row
            for row in rows
            if row["pipeline"]
            == pipeline["name"]
        ]

        row_count = len(pipeline_rows)

        if row_count == 0:
            continue

        abstention_rows = [
            row
            for row in pipeline_rows
            if (
                row["metrics"][
                    "abstention_correct"
                ]
                is not None
            )
        ]

        summary = {
            "name": pipeline["name"],
            "label": pipeline["label"],
            "cases": row_count,
            "faithfulness": round(
                mean(
                    row["metrics"][
                        "faithfulness"
                    ]
                    for row in pipeline_rows
                ),
                4,
            ),
            "answer_relevance": round(
                mean(
                    row["metrics"][
                        "answer_relevance"
                    ]
                    for row in pipeline_rows
                ),
                4,
            ),
            "context_precision": round(
                mean(
                    row["metrics"][
                        "context_precision"
                    ]
                    for row in pipeline_rows
                ),
                4,
            ),
            "context_recall": round(
                mean(
                    row["metrics"][
                        "context_recall"
                    ]
                    for row in pipeline_rows
                ),
                4,
            ),
            "pass_rate": round(
                mean(
                    1.0 if row["passed"] else 0.0
                    for row in pipeline_rows
                ),
                4,
            ),
            "abstention_accuracy": (
                round(
                    mean(
                        1.0
                        if row["metrics"][
                            "abstention_correct"
                        ]
                        else 0.0
                        for row in (
                            abstention_rows
                        )
                    ),
                    4,
                )
                if abstention_rows
                else None
            ),
            "avg_latency_ms": round(
                mean(
                    row["latency_ms"]
                    for row in pipeline_rows
                ),
                1,
            ),
            "total_tokens": sum(
                row["total_tokens"]
                for row in pipeline_rows
            ),
            "failures": sum(
                1
                for row in pipeline_rows
                if row["error"]
            ),
        }

        summary["composite_score"] = round(
            0.30 * summary["faithfulness"]
            + 0.20
            * summary["answer_relevance"]
            + 0.20
            * summary["context_precision"]
            + 0.20
            * summary["context_recall"]
            + 0.10 * summary["pass_rate"],
            4,
        )

        summaries.append(summary)

    comparison = _compare(summaries)

    return {
        "dataset": dataset,
        "case_count": len(cases),
        "metrics_are_proxies": True,
        "pipelines": summaries,
        "comparison": comparison,
    }


def _compare(
    summaries: list[dict],
) -> dict:
    if len(summaries) < 2:
        return {
            "winner": (
                summaries[0]["name"]
                if summaries
                else None
            ),
            "deltas": {},
        }

    baseline = next(
        (
            item
            for item in summaries
            if item["name"] == "baseline"
        ),
        summaries[0],
    )

    enhanced = next(
        (
            item
            for item in summaries
            if item["name"] == "enhanced"
        ),
        summaries[-1],
    )

    deltas = {
        key: round(
            enhanced[key]
            - baseline[key],
            4,
        )
        for key in (
            *METRIC_KEYS,
            "pass_rate",
            "composite_score",
        )
        if (
            baseline.get(key) is not None
            and enhanced.get(key) is not None
        )
    }

    return {
        "winner": (
            enhanced["name"]
            if enhanced["composite_score"]
            >= baseline["composite_score"]
            else baseline["name"]
        ),
        "baseline": baseline["name"],
        "candidate": enhanced["name"],
        "deltas": deltas,
    }
