from uuid import uuid4

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Request,
    Response,
    status,
)
from langgraph.errors import GraphRecursionError
from langgraph.types import Command
from sqlalchemy.ext.asyncio import AsyncSession
import time

from app.agents.dependencies import (
    get_planning_graph,
)
from app.core.config import settings
from app.core.errors import AgentExecutionError
from app.db.dependencies import get_db
from app.schemas.planning import (
    PlanEvidenceRead,
    PlanRequest,
    PlanResponse,
    PlanResumeRequest,
    PlanStepRead,
)
from app.services.interaction_recorder import (
    record_answer_interactions,
)
from app.services.observability import (
    record_llm_request,
)
from app.services.rate_limiter import (
    check_rag_rate_limit,
)
from app.services.token_usage import (
    estimate_prompt_tokens,
    estimate_tokens,
)

router = APIRouter(
    prefix="/agent",
    tags=["Planning agent"],
)


def _config(
    thread_id: str,
    run_name: str,
) -> dict:
    return {
        "configurable": {
            "thread_id": thread_id,
        },
        "recursion_limit": (
            settings.agent_recursion_limit + 18
        ),
        "run_name": run_name,
        "tags": [
            "agent",
            "planning",
        ],
        "metadata": {
            "thread_id": thread_id,
            "agent_mode": "planning",
        },
    }


def _build_response(
    result: dict,
    thread_id: str,
    task: str,
) -> PlanResponse:
    interrupts = result.get(
        "__interrupt__",
        (),
    )

    step_results = {
        item["id"]: item
        for item in result.get(
            "step_results",
            [],
        )
    }

    plan_steps = []

    for step in result.get("plan", []):
        outcome = step_results.get(
            step["id"],
            {},
        )

        plan_steps.append(
            PlanStepRead(
                id=step["id"],
                title=step["title"],
                action=step["action"],
                query=step.get("query", ""),
                status=outcome.get("status"),
                evidence_count=outcome.get(
                    "evidence_count",
                    0,
                ),
            )
        )

    evidence = [
        PlanEvidenceRead(**item)
        for item in result.get(
            "evidence",
            [],
        )
    ]

    response_status = result.get(
        "status",
        "completed",
    )

    interrupt_payload = None

    if interrupts:
        pending = interrupts[0]

        interrupt_payload = {
            "id": pending.id,
            "value": pending.value,
        }

        response_status = "interrupted"

    if response_status not in (
        "completed",
        "rejected",
    ):
        response_status = "interrupted"

    return PlanResponse(
        thread_id=thread_id,
        status=response_status,
        task=task,
        plan_summary=result.get(
            "plan_summary",
            "",
        ),
        plan_steps=plan_steps,
        dependencies=result.get(
            "dependencies",
            [],
        ),
        risks=result.get("risks", []),
        evidence=evidence,
        draft=result.get("draft"),
        critique=result.get("critique"),
        issues=result.get("issues", []),
        confidence=result.get(
            "confidence"
        ),
        verification_passed=result.get(
            "verification_passed"
        ),
        revision_count=result.get(
            "revision_count",
            0,
        ),
        answer=(
            result.get("final_answer")
            or result.get("draft")
        ),
        approval=result.get("approval"),
        interrupt=interrupt_payload,
    )


@router.post(
    "/plan",
    response_model=PlanResponse,
)
async def plan_task(
    payload: PlanRequest,
    request: Request,
    response: Response,
    session: AsyncSession = Depends(get_db),
    graph=Depends(get_planning_graph),
):
    client_identifier = (
        request.client.host
        if request.client
        else "unknown"
    )

    decision = await check_rag_rate_limit(
        client_identifier
    )

    headers = {
        "X-RateLimit-Limit": str(
            decision.limit
        ),
        "X-RateLimit-Remaining": str(
            decision.remaining
        ),
        "X-RateLimit-Reset": str(
            decision.retry_after
        ),
    }

    if not decision.allowed:
        raise HTTPException(
            status_code=(
                status.HTTP_429_TOO_MANY_REQUESTS
            ),
            detail=(
                "Planning request rate limit "
                "exceeded."
            ),
            headers={
                **headers,
                "Retry-After": str(
                    decision.retry_after
                ),
            },
        )

    for key, value in headers.items():
        response.headers[key] = value

    thread_id = (
        payload.thread_id
        or uuid4().hex
    )

    started = time.perf_counter()

    try:
        result = await graph.ainvoke(
            {
                "task": payload.task,
                "limit": payload.limit,
                "min_similarity": (
                    payload.min_similarity
                ),
                "max_revisions": (
                    payload.max_revisions
                ),
            },
            config=_config(
                thread_id,
                "planning_request",
            ),
        )

    except GraphRecursionError as exc:
        raise AgentExecutionError(
            "Planning failed because the graph "
            "exceeded its recursion limit."
        ) from exc

    latency_ms = int(
        (time.perf_counter() - started)
        * 1000
    )

    built = _build_response(
        result,
        thread_id,
        payload.task,
    )

    evidence_context = "\n\n".join(
        item.content
        for item in built.evidence
    )

    await record_llm_request(
        session,
        endpoint="/agent/plan",
        pipeline="planning",
        question=payload.task,
        route="planning",
        latency_ms=latency_ms,
        prompt_tokens=estimate_prompt_tokens(
            payload.task,
            evidence_context,
        ),
        completion_tokens=estimate_tokens(
            built.answer
        ),
        success=True,
    )

    await record_answer_interactions(
        session,
        payload.user_id,
        payload.task,
        [item.document_id for item in built.evidence],
        event_type="ask",
    )

    return built


@router.post(
    "/plan/resume",
    response_model=PlanResponse,
)
async def resume_plan(
    payload: PlanResumeRequest,
    graph=Depends(get_planning_graph),
):
    try:
        result = await graph.ainvoke(
            Command(
                resume={
                    "approved": (
                        payload.approved
                    ),
                    "note": payload.note,
                }
            ),
            config=_config(
                payload.thread_id,
                "planning_resume",
            ),
        )

    except GraphRecursionError as exc:
        raise AgentExecutionError(
            "Planning failed because the graph "
            "exceeded its recursion limit."
        ) from exc

    return _build_response(
        result,
        payload.thread_id,
        result.get("task", ""),
    )
