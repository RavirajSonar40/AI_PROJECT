from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.evaluation import (
    EvaluationCase,
    EvaluationRun,
)


class EvaluationRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_run(
        self,
        dataset: str,
        pipelines: list[dict],
        case_count: int,
    ) -> EvaluationRun:
        run = EvaluationRun(
            dataset=dataset,
            status="running",
            pipelines=pipelines,
            case_count=case_count,
        )

        self.session.add(run)

        await self.session.commit()
        await self.session.refresh(run)

        return run

    async def add_case(
        self,
        run_id: int,
        pipeline: str,
        question: str,
        expected_answer: str | None,
        expected_document_ids: list[int],
        answer: str | None,
        retrieved_document_ids: list[int],
        metrics: dict,
        latency_ms: int,
        prompt_tokens: int,
        completion_tokens: int,
        passed: bool,
        error: str | None = None,
    ) -> EvaluationCase:
        record = EvaluationCase(
            run_id=run_id,
            pipeline=pipeline,
            question=question,
            expected_answer=expected_answer,
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
            completion_tokens=completion_tokens,
            total_tokens=(
                prompt_tokens
                + completion_tokens
            ),
            passed=passed,
            error=error,
        )

        self.session.add(record)

        await self.session.commit()
        await self.session.refresh(record)

        return record

    async def complete_run(
        self,
        run_id: int,
        summary: dict,
    ) -> None:
        run = await self.get_run(run_id)

        if run is None:
            return

        from datetime import datetime, timezone

        run.status = "completed"
        run.summary = summary
        run.completed_at = datetime.now(
            timezone.utc
        )

        await self.session.commit()

    async def fail_run(
        self,
        run_id: int,
        error: str,
    ) -> None:
        run = await self.get_run(run_id)

        if run is None:
            return

        from datetime import datetime, timezone

        run.status = "failed"
        run.error = error
        run.completed_at = datetime.now(
            timezone.utc
        )

        await self.session.commit()

    async def get_run(
        self,
        run_id: int,
    ) -> EvaluationRun | None:
        result = await self.session.execute(
            select(EvaluationRun).where(
                EvaluationRun.id == run_id
            )
        )

        return result.scalar_one_or_none()

    async def list_runs(
        self,
        limit: int = 20,
    ) -> list[EvaluationRun]:
        result = await self.session.execute(
            select(EvaluationRun)
            .order_by(
                EvaluationRun.started_at.desc()
            )
            .limit(limit)
        )

        return list(result.scalars().all())

    async def list_cases(
        self,
        run_id: int,
    ) -> list[EvaluationCase]:
        result = await self.session.execute(
            select(EvaluationCase)
            .where(
                EvaluationCase.run_id == run_id
            )
            .order_by(
                EvaluationCase.pipeline,
                EvaluationCase.id,
            )
        )

        return list(result.scalars().all())
