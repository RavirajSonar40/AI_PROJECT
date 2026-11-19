import time
from uuid import uuid4

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Request,
    Response,
    status,
)
from langgraph.types import (
    Command,
)
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.dependencies import (
    get_agent_graph,
)
from app.core.config import settings
from app.db.dependencies import get_db
from app.services.interaction_recorder import (
    record_answer_interactions,
)
from app.services.observability import (
    record_llm_request,
)
from app.services.token_usage import (
    estimate_prompt_tokens,
    estimate_tokens,
)
from app.schemas.agent import (
    AgentRequest,
    AgentResponse,
)
from app.services.rate_limiter import (
    check_rag_rate_limit,
)

from langgraph.errors import (
    GraphRecursionError,
)

from app.core.errors import (
    AgentExecutionError,
)


class AgentResumeRequest(BaseModel):
    thread_id: str = Field(
        min_length=1,
        max_length=128,
    )

    approved: bool

    note: str | None = Field(
        default=None,
        max_length=500,
    )


router = APIRouter(
    prefix="/agent",
    tags=["agent"],
)


@router.post(
    "/ask",
    response_model=AgentResponse,
)
async def ask_agent(
    payload: AgentRequest,
    request: Request,
    response: Response,
    session: AsyncSession = Depends(get_db),
    graph=Depends(get_agent_graph),
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
                "Agent request rate limit exceeded."
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

    config = {
        "configurable": {
            "thread_id": thread_id,
        },
        "recursion_limit": (
            settings.agent_recursion_limit
        ),
        "run_name": "agent_request",
        "tags": [
            "agent",
            settings.agent_mode,
        ],
        "metadata": {
            "thread_id": thread_id,
            "agent_mode": (
                settings.agent_mode
            ),
        },
    }

    started = time.perf_counter()

    try:
        result = await graph.ainvoke(
            {
                "question": payload.question,
                "limit": payload.limit,
                "min_similarity": (
                    payload.min_similarity
                ),
            },
            config=config,
        )
    except GraphRecursionError as exc:
        raise AgentExecutionError(
            "Agent execution failed due to recursion limit."
        ) from exc

    latency_ms = int(
        (time.perf_counter() - started) * 1000
    )

    interrupts = result.get(
        "__interrupt__",
        (),
    )

    if interrupts:
        pending = interrupts[0]

        return AgentResponse(
            thread_id=thread_id,
            status="interrupted",
            question=payload.question,
            interrupt={
                "id": pending.id,
                "value": pending.value,
            },
        )

    sources = result.get("sources", []) or []

    response_payload = AgentResponse(
        thread_id=thread_id,
        status="completed",
        question=payload.question,
        answer=result.get("answer"),
        route=result.get("route"),
        handled_by=result.get(
            "handled_by"
        ),
        tool_used=result.get(
            "tool_used"
        ),
        sources=sources,
    )

    context = "\n\n".join(
        (
            str(source.get("content", ""))
            if isinstance(source, dict)
            else str(
                getattr(
                    source,
                    "content",
                    "",
                )
            )
        )
        for source in sources
    )

    await record_llm_request(
        session,
        endpoint="/agent/ask",
        pipeline="agent",
        question=payload.question,
        route=result.get("route"),
        latency_ms=latency_ms,
        prompt_tokens=estimate_prompt_tokens(
            payload.question,
            context,
        ),
        completion_tokens=estimate_tokens(
            result.get("answer")
        ),
        success=True,
    )

    await record_answer_interactions(
        session,
        payload.user_id,
        payload.question,
        sources,
    )

    return response_payload


@router.post(
    "/resume",
    response_model=AgentResponse,
)
async def resume_agent(
    payload: AgentResumeRequest,
    graph=Depends(get_agent_graph),
):
    config = {
        "configurable": {
            "thread_id": (
                payload.thread_id
            ),
        },
        "recursion_limit": (
            settings.agent_recursion_limit
        ),
        "run_name": "agent_resume",
        "tags": [
            "agent",
            "human_in_the_loop",
        ],
        "metadata": {
            "thread_id": (
                payload.thread_id
            ),
            "agent_mode": (
                settings.agent_mode
            ),
        },
    }

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
            config=config,
        )
    except GraphRecursionError as exc:
        raise AgentExecutionError(
            "Agent execution failed due to recursion limit."
        ) from exc

    interrupts = result.get(
        "__interrupt__",
        (),
    )

    if interrupts:
        pending = interrupts[0]

        return AgentResponse(
            thread_id=(
                payload.thread_id
            ),
            status="interrupted",
            question=result.get(
                "question"
            ),
            interrupt={
                "id": pending.id,
                "value": pending.value,
            },
        )

    return AgentResponse(
        thread_id=payload.thread_id,
        status="completed",
        question=result.get(
            "question"
        ),
        answer=result.get(
            "answer"
        ),
        route=result.get(
            "route"
        ),
        handled_by=result.get(
            "handled_by"
        ),
        tool_used=result.get(
            "tool_used"
        ),
        sources=result.get(
            "sources",
            [],
        ),
    )