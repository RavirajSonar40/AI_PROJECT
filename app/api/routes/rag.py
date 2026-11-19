import time

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Request,
    Response,
    status,
)
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.dependencies import get_db
from app.repositories.document_chunk import (
    DocumentChunkRepository,
)
from app.schemas.rag import (
    RAGRequest,
    RAGResponse,
    RAGSource,
)
from app.services.chat_model_provider import (
    ChatModelProvider,
)
from app.services.embedding_service import (
    EmbeddingGenerationError,
)
from app.services.interaction_recorder import (
    record_answer_interactions,
)
from app.services.observability import (
    record_llm_request,
)
from app.services.ollama_provider import (
    LLMProviderError,
)
from app.services.rag_service import RAGService
from app.services.rate_limiter import (
    check_rag_rate_limit,
)
from app.services.token_usage import (
    estimate_prompt_tokens,
    estimate_tokens,
)


router = APIRouter(
    prefix="/rag",
    tags=["RAG"],
)


@router.post(
    "/ask",
    response_model=RAGResponse,
)
async def ask_rag(
    payload: RAGRequest,
    request: Request,
    response: Response,
    session: AsyncSession = Depends(get_db),
):
    client_identifier = (
        request.client.host
        if request.client
        else "unknown"
    )

    decision = await check_rag_rate_limit(
        client_identifier
    )

    rate_limit_headers = {
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
                "RAG request rate limit exceeded."
            ),
            headers={
                **rate_limit_headers,
                "Retry-After": str(
                    decision.retry_after
                ),
            },
        )

    for header, value in (
        rate_limit_headers.items()
    ):
        response.headers[header] = value

    chunk_repository = DocumentChunkRepository(
        session
    )

    service = RAGService(
        chunk_retriever=chunk_repository,
        llm=ChatModelProvider(),
    )

    started = time.perf_counter()

    try:
        answer, matches = await service.answer(
            question=payload.question,
            limit=payload.limit,
            min_similarity=payload.min_similarity,
        )

    except (
        EmbeddingGenerationError,
        LLMProviderError,
    ) as exc:
        await record_llm_request(
            session,
            endpoint="/rag/ask",
            pipeline="rag",
            question=payload.question,
            route="knowledge",
            latency_ms=int(
                (
                    time.perf_counter()
                    - started
                )
                * 1000
            ),
            prompt_tokens=0,
            completion_tokens=0,
            success=False,
            error=str(exc),
        )

        raise HTTPException(
            status_code=(
                status.HTTP_503_SERVICE_UNAVAILABLE
            ),
            detail=str(exc),
        ) from exc

    sources = [
        RAGSource(
            chunk_id=chunk.id,
            document_id=chunk.document_id,
            position=chunk.position,
            similarity=round(
                1.0 - distance,
                4,
            ),
            content=chunk.content,
        )
        for chunk, distance in matches
    ]

    latency_ms = int(
        (time.perf_counter() - started) * 1000
    )

    context = "\n\n".join(
        source.content
        for source in sources
    )

    await record_llm_request(
        session,
        endpoint="/rag/ask",
        pipeline="rag",
        question=payload.question,
        route="knowledge",
        latency_ms=latency_ms,
        prompt_tokens=estimate_prompt_tokens(
            payload.question,
            context,
        ),
        completion_tokens=estimate_tokens(
            answer
        ),
        usage_source=(
            service.llm.last_usage.source
            if getattr(service.llm, "last_usage", None)
            else "estimated"
        ),
        success=True,
    )

    await record_answer_interactions(
        session,
        payload.user_id,
        payload.question,
        sources,
    )

    return RAGResponse(
        question=payload.question,
        answer=answer,
        sources=sources,
    )
