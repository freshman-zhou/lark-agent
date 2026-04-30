import uuid
from datetime import datetime

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from packages.domain.task.task_status import TaskJobStatus, TaskJobType
from packages.infrastructure.db.models.task_job_model import TaskJobModel


class TaskJobRepository:
    def __init__(self, db: Session):
        self.db = db

    def create_pending_langgraph_job(
        self,
        task_id: str,
        max_retries: int = 3,
    ) -> TaskJobModel:
        job = TaskJobModel(
            id=f"job_{uuid.uuid4().hex[:12]}",
            task_id=task_id,
            job_type=TaskJobType.RUN_LANGGRAPH.value,
            status=TaskJobStatus.PENDING.value,
            idempotency_key=f"run_langgraph:{task_id}",
            retry_count=0,
            max_retries=max_retries,
            error_message=None,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            started_at=None,
            finished_at=None,
        )

        self.db.add(job)
        return job

    def get_by_id(self, job_id: str) -> TaskJobModel | None:
        return self.db.get(TaskJobModel, job_id)

    def list_by_task(self, task_id: str) -> list[TaskJobModel]:
        stmt = (
            select(TaskJobModel)
            .where(TaskJobModel.task_id == task_id)
            .order_by(TaskJobModel.created_at.asc())
        )

        return list(self.db.execute(stmt).scalars().all())

    def get_latest_by_task(self, task_id: str) -> TaskJobModel | None:
        stmt = (
            select(TaskJobModel)
            .where(TaskJobModel.task_id == task_id)
            .order_by(TaskJobModel.created_at.desc())
            .limit(1)
        )

        return self.db.scalar(stmt)

    def list_recent(
        self,
        limit: int = 50,
        status: str | None = None,
    ) -> list[TaskJobModel]:
        stmt = select(TaskJobModel)

        if status:
            stmt = stmt.where(TaskJobModel.status == status)

        stmt = stmt.order_by(TaskJobModel.created_at.desc()).limit(limit)

        return list(self.db.execute(stmt).scalars().all())

    def claim_next_pending_job(self) -> TaskJobModel | None:
        candidate = self.db.scalar(
            select(TaskJobModel)
            .where(TaskJobModel.status == TaskJobStatus.PENDING.value)
            .order_by(TaskJobModel.created_at.asc())
            .limit(1)
        )

        if candidate is None:
            return None

        now = datetime.utcnow()

        stmt = (
            update(TaskJobModel)
            .where(TaskJobModel.id == candidate.id)
            .where(TaskJobModel.status == TaskJobStatus.PENDING.value)
            .values(
                status=TaskJobStatus.RUNNING.value,
                started_at=now,
                updated_at=now,
            )
        )

        result = self.db.execute(stmt)

        if result.rowcount != 1:
            self.db.rollback()
            return None

        self.db.commit()

        return self.get_by_id(candidate.id)

    def mark_success(self, job_id: str) -> TaskJobModel:
        job = self.get_by_id(job_id)

        if job is None:
            raise ValueError(f"Task job not found: {job_id}")

        now = datetime.utcnow()

        job.status = TaskJobStatus.SUCCESS.value
        job.error_message = None
        job.finished_at = now
        job.updated_at = now

        self.db.commit()
        self.db.refresh(job)

        return job

    def mark_failed(self, job_id: str, error_message: str) -> TaskJobModel:
        job = self.get_by_id(job_id)

        if job is None:
            raise ValueError(f"Task job not found: {job_id}")

        now = datetime.utcnow()

        job.status = TaskJobStatus.FAILED.value
        job.error_message = error_message
        job.finished_at = now
        job.updated_at = now

        self.db.commit()
        self.db.refresh(job)

        return job

    def mark_retrying_or_failed(
        self,
        job_id: str,
        error_message: str,
    ) -> TaskJobModel:
        job = self.get_by_id(job_id)

        if job is None:
            raise ValueError(f"Task job not found: {job_id}")

        now = datetime.utcnow()

        if job.retry_count < job.max_retries:
            job.retry_count += 1
            job.status = TaskJobStatus.PENDING.value
            job.error_message = error_message
            job.started_at = None
            job.finished_at = None
            job.updated_at = now
        else:
            job.status = TaskJobStatus.FAILED.value
            job.error_message = error_message
            job.finished_at = now
            job.updated_at = now

        self.db.commit()
        self.db.refresh(job)

        return job

    def cancel_pending_by_task(self, task_id: str) -> int:
        now = datetime.utcnow()

        stmt = (
            update(TaskJobModel)
            .where(TaskJobModel.task_id == task_id)
            .where(TaskJobModel.status == TaskJobStatus.PENDING.value)
            .values(
                status=TaskJobStatus.CANCELLED.value,
                updated_at=now,
                finished_at=now,
            )
        )

        result = self.db.execute(stmt)
        self.db.commit()

        return int(result.rowcount or 0)