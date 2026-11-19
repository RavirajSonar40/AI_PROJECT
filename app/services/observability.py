"""Request telemetry used by the observability dashboard.

Every user-facing AI endpoint writes one row. Writes are best-effort: a
telemetry failure must never break the answer the user asked for.
"""

from __future__ import annotations

from app.core.config import settings
from app.core.metrics import (
    LLM_LATENCY_SECONDS,
    LLM_REQUESTS,
    LLM_TOKENS,
)
from app.repositories.observability import (
    ObservabilityRepository,
)
from sqlalchemy.ext.asyncio import AsyncSession


async def record_llm_request(
    session: AsyncSession,
    *,
    endpoint: str,
    pipeline: str,
    question: str | None,
    route: str | None,
    latency_ms: int,
    prompt_tokens: int,
    completion_tokens: int,
    usage_source: str = "estimated",
    success: bool = True,
    error: str | None = None,
) -> None:
    model = _active_model_name()

    try:
        repository = ObservabilityRepository(
            session
        )

        await repository.record(
            endpoint=endpoint,
            pipeline=pipeline,
            question=question,
            route=route,
            model=model,
            latency_ms=latency_ms,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            usage_source=usage_source,
            success=success,
            error=error,
        )

    except Exception:
        # Telemetry is not allowed to break the request.
        await session.rollback()

    try:
        LLM_REQUESTS.labels(
            endpoint=endpoint,
            pipeline=pipeline,
            success=(
                "true" if success else "false"
            ),
        ).inc()

        LLM_LATENCY_SECONDS.labels(
            endpoint=endpoint,
            pipeline=pipeline,
        ).observe(latency_ms / 1000)

        LLM_TOKENS.labels(
            endpoint=endpoint,
            direction="prompt",
        ).inc(prompt_tokens)

        LLM_TOKENS.labels(
            endpoint=endpoint,
            direction="completion",
        ).inc(completion_tokens)

    except Exception:
        pass


def _active_model_name() -> str:
    provider = settings.llm_provider

    if provider == "groq":
        return settings.groq_model

    if provider == "bazaarlink":
        return settings.bazaarlink_model

    return settings.ollama_model


def _percentile(
    values: list[int],
    percentile_rank: float,
) -> float:
    if not values:
        return 0.0

    ordered = sorted(values)

    index = int(
        round(
            (len(ordered) - 1)
            * percentile_rank
        )
    )

    return float(ordered[index])


async def build_overview(
    session: AsyncSession,
    hours: int = 24,
) -> dict:
    repository = ObservabilityRepository(
        session
    )

    records = await repository.since(hours)
    recent = await repository.recent(15)
    total_all_time = (
        await repository.total_count()
    )

    latencies = [
        record.latency_ms
        for record in records
    ]

    successes = sum(
        1 for record in records if record.success
    )

    failures = len(records) - successes

    prompt_tokens = sum(
        record.prompt_tokens for record in records
    )

    completion_tokens = sum(
        record.completion_tokens
        for record in records
    )

    per_endpoint: dict[str, dict] = {}

    for record in records:
        bucket = per_endpoint.setdefault(
            record.endpoint,
            {
                "endpoint": record.endpoint,
                "requests": 0,
                "failures": 0,
                "latency_ms": [],
                "tokens": 0,
            },
        )

        bucket["requests"] += 1
        bucket["latency_ms"].append(
            record.latency_ms
        )
        bucket["tokens"] += record.total_tokens

        if not record.success:
            bucket["failures"] += 1

    endpoints = []

    for bucket in per_endpoint.values():
        endpoints.append(
            {
                "endpoint": bucket["endpoint"],
                "requests": bucket["requests"],
                "failures": bucket["failures"],
                "avg_latency_ms": round(
                    sum(bucket["latency_ms"])
                    / len(bucket["latency_ms"]),
                    1,
                ),
                "tokens": bucket["tokens"],
            }
        )

    endpoints.sort(
        key=lambda item: item["requests"],
        reverse=True,
    )

    failed_queries = [
        {
            "endpoint": record.endpoint,
            "question": record.question,
            "route": record.route,
            "error": record.error,
            "created_at": (
                record.created_at.isoformat()
            ),
        }
        for record in records
        if not record.success
    ][:10]

    return {
        "window_hours": hours,
        "model": _active_model_name(),
        "provider": settings.llm_provider,
        "requests": len(records),
        "requests_all_time": total_all_time,
        "successes": successes,
        "failures": failures,
        "error_rate": round(
            (
                failures / len(records)
                if records
                else 0.0
            ),
            4,
        ),
        "avg_latency_ms": round(
            (
                sum(latencies) / len(latencies)
                if latencies
                else 0.0
            ),
            1,
        ),
        "p50_latency_ms": _percentile(
            latencies,
            0.50,
        ),
        "p95_latency_ms": _percentile(
            latencies,
            0.95,
        ),
        "p99_latency_ms": _percentile(
            latencies,
            0.99,
        ),
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "total_tokens": (
            prompt_tokens + completion_tokens
        ),
        "estimated_cost_usd": round(
            _estimate_cost(
                prompt_tokens,
                completion_tokens,
            ),
            6,
        ),
        "tokens_are_estimated": not any(
            record.usage_source == "provider"
            for record in records
        ),
        "usage_source": (
            "provider"
            if records and all(
                record.usage_source == "provider"
                for record in records
            )
            else "mixed" if any(
                record.usage_source == "provider"
                for record in records
            ) else "estimated"
        ),
        "endpoints": endpoints,
        "failed_queries": failed_queries,
        "recent_requests": [
            {
                "endpoint": record.endpoint,
                "pipeline": record.pipeline,
                "question": record.question,
                "route": record.route,
                "latency_ms": record.latency_ms,
                "total_tokens": record.total_tokens,
                "success": record.success,
                "created_at": (
                    record.created_at.isoformat()
                ),
            }
            for record in recent
        ],
    }


def _estimate_cost(
    prompt_tokens: int,
    completion_tokens: int,
) -> float:
    """Rough Groq pricing estimate, kept intentionally simple."""

    # openai/gpt-oss-120b on Groq is billed per million tokens.
    input_price = 0.15
    output_price = 0.75

    return (
        prompt_tokens / 1_000_000
    ) * input_price + (
        completion_tokens / 1_000_000
    ) * output_price
