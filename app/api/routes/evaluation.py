from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    status,
)
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.dependencies import get_db
from app.evaluation.rag_evaluator import (
    list_datasets,
    run_evaluation,
)
from app.repositories.evaluation import (
    EvaluationRepository,
)
from app.schemas.evaluation import (
    EvaluationRequest,
)

router = APIRouter(
    prefix="/evaluation",
    tags=["Evaluation"],
)


def _serialize_run(run) -> dict:
    return {
        "id": run.id,
        "dataset": run.dataset,
        "status": run.status,
        "case_count": run.case_count,
        "pipelines": run.pipelines,
        "summary": run.summary,
        "error": run.error,
        "started_at": (
            run.started_at.isoformat()
            if run.started_at
            else None
        ),
        "completed_at": (
            run.completed_at.isoformat()
            if run.completed_at
            else None
        ),
    }


@router.get("/datasets")
async def get_datasets():
    return list_datasets()


@router.post("/runs")
async def create_evaluation_run(
    payload: EvaluationRequest,
    session: AsyncSession = Depends(get_db),
):
    try:
        result = await run_evaluation(
            session=session,
            dataset_name=payload.dataset,
            pipeline_names=payload.pipelines,
            max_cases=payload.max_cases,
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=(
                status.HTTP_400_BAD_REQUEST
            ),
            detail=str(exc),
        ) from exc

    except Exception as exc:
        raise HTTPException(
            status_code=(
                status.HTTP_500_INTERNAL_SERVER_ERROR
            ),
            detail=(
                "The evaluation run failed: "
                f"{exc}"
            ),
        ) from exc

    return result


@router.get("/runs")
async def list_evaluation_runs(
    limit: int = 20,
    session: AsyncSession = Depends(get_db),
):
    repository = EvaluationRepository(session)

    runs = await repository.list_runs(
        limit=max(1, min(limit, 100))
    )

    return [
        _serialize_run(run) for run in runs
    ]


@router.get("/runs/{run_id}")
async def get_evaluation_run(
    run_id: int,
    session: AsyncSession = Depends(get_db),
):
    repository = EvaluationRepository(session)

    run = await repository.get_run(run_id)

    if run is None:
        raise HTTPException(
            status_code=(
                status.HTTP_404_NOT_FOUND
            ),
            detail="Evaluation run not found.",
        )

    cases = await repository.list_cases(
        run_id
    )

    return {
        "run": _serialize_run(run),
        "cases": [
            {
                "id": case.id,
                "pipeline": case.pipeline,
                "question": case.question,
                "expected_answer": (
                    case.expected_answer
                ),
                "expected_document_ids": (
                    case.expected_document_ids
                ),
                "answer": case.answer,
                "retrieved_document_ids": (
                    case.retrieved_document_ids
                ),
                "metrics": case.metrics,
                "latency_ms": case.latency_ms,
                "prompt_tokens": (
                    case.prompt_tokens
                ),
                "completion_tokens": (
                    case.completion_tokens
                ),
                "total_tokens": (
                    case.total_tokens
                ),
                "passed": case.passed,
                "error": case.error,
            }
            for case in cases
        ],
    }
