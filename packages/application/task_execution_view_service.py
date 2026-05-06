from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from packages.infrastructure.db.repositories.agent_action_repository import (
    AgentActionRepository,
)
from packages.infrastructure.db.repositories.artifact_repository import ArtifactRepository
from packages.infrastructure.db.repositories.task_job_repository import TaskJobRepository
from packages.infrastructure.db.repositories.task_repository import TaskRepository


class TaskExecutionViewService:
    """
    任务运行可见性查询服务。

    聚合：
    1. tasks 主状态；
    2. task_jobs 队列状态；
    3. agent_actions 执行日志；
    4. delivery.prepare_result 的最终交付结果；
    5. timeline 执行时间线。
    """

    def __init__(self, db: Session):
        self.db = db
        self.task_repository = TaskRepository(db)
        self.task_job_repository = TaskJobRepository(db)
        self.action_repository = AgentActionRepository(db)
        self.artifact_repository = ArtifactRepository(db)

    def get_execution_detail(self, task_id: str) -> dict[str, Any]:
        task_model = self.task_repository.get_model_by_id(task_id)
        jobs = self.task_job_repository.list_by_task(task_id)
        actions = self.action_repository.list_by_task(task_id)
        artifacts = self.artifact_repository.list_by_task(task_id)

        serialized_jobs = [self._serialize_job(job) for job in jobs]
        serialized_actions = [self._serialize_action(action) for action in actions]

        return {
            "task": self._serialize_task(task_model),
            "latest_job": serialized_jobs[-1] if serialized_jobs else None,
            "jobs": serialized_jobs,
            "actions": serialized_actions,
            "artifacts": [self._serialize_artifact(item) for item in artifacts],
            "delivery_result": self._extract_delivery_result(actions),
            "summary": self._build_summary(
                task_model=task_model,
                jobs=jobs,
                actions=actions,
            ),
            "timeline": self._build_timeline(
                task_model=task_model,
                jobs=jobs,
                actions=actions,
            ),
        }

    def get_execution_summary(self, task_id: str) -> dict[str, Any]:
        task_model = self.task_repository.get_model_by_id(task_id)
        jobs = self.task_job_repository.list_by_task(task_id)
        actions = self.action_repository.list_by_task(task_id)

        return self._build_summary(
            task_model=task_model,
            jobs=jobs,
            actions=actions,
        )

    def list_recent_jobs(
        self,
        limit: int = 50,
        status: str | None = None,
    ) -> dict[str, Any]:
        jobs = self.task_job_repository.list_recent(
            limit=limit,
            status=status,
        )

        return {
            "items": [self._serialize_job(job) for job in jobs],
            "count": len(jobs),
        }

    def _build_summary(
        self,
        task_model,
        jobs: list,
        actions: list,
    ) -> dict[str, Any]:
        latest_job = jobs[-1] if jobs else None

        total_actions = len(actions)
        success_actions = len(
            [
                action
                for action in actions
                if self._value(action.status) == "SUCCESS"
            ]
        )
        failed_actions = len(
            [
                action
                for action in actions
                if self._value(action.status) == "FAILED"
            ]
        )
        running_actions = len(
            [
                action
                for action in actions
                if self._value(action.status) == "RUNNING"
            ]
        )

        task_status = self._value(task_model.status)

        return {
            "task_id": task_model.id,
            "task_status": task_status,
            "task_title": task_model.title,
            "task_type": self._value(task_model.task_type),
            "progress": task_model.progress,
            "current_step": task_model.current_step,
            "confirmed_by": getattr(task_model, "confirmed_by", None),
            "confirmed_at": self._dt(getattr(task_model, "confirmed_at", None)),
            "job_status": self._value(latest_job.status) if latest_job else None,
            "retry_count": latest_job.retry_count if latest_job else 0,
            "max_retries": latest_job.max_retries if latest_job else 0,
            "latest_error": self._latest_error(
                task_model=task_model,
                latest_job=latest_job,
                actions=actions,
            ),
            "total_actions": total_actions,
            "success_actions": success_actions,
            "failed_actions": failed_actions,
            "running_actions": running_actions,
            "is_finished": task_status in {
                "COMPLETED",
                "FAILED",
                "CANCELLED",
            },
            "created_at": self._dt(task_model.created_at),
            "updated_at": self._dt(task_model.updated_at),
        }

    def _build_timeline(
        self,
        task_model,
        jobs: list,
        actions: list,
    ) -> list[dict[str, Any]]:
        timeline: list[dict[str, Any]] = []

        timeline.append(
            {
                "type": "TASK_CREATED",
                "title": "任务已创建",
                "status": "SUCCESS",
                "message": task_model.title,
                "time": self._dt(task_model.created_at),
                "sort_time": task_model.created_at,
            }
        )

        confirmed_at = getattr(task_model, "confirmed_at", None)

        if confirmed_at:
            timeline.append(
                {
                    "type": "TASK_CONFIRMED",
                    "title": "任务已确认",
                    "status": "SUCCESS",
                    "message": f"确认人：{getattr(task_model, 'confirmed_by', None) or '-'}",
                    "time": self._dt(confirmed_at),
                    "sort_time": confirmed_at,
                }
            )

        for job in jobs:
            timeline.append(
                {
                    "type": "JOB_CREATED",
                    "title": "执行任务已入队",
                    "status": self._value(job.status),
                    "message": f"job_id={job.id}, retry={job.retry_count}/{job.max_retries}",
                    "time": self._dt(job.created_at),
                    "sort_time": job.created_at,
                }
            )

            if job.started_at:
                timeline.append(
                    {
                        "type": "JOB_STARTED",
                        "title": "worker 已领取任务",
                        "status": self._value(job.status),
                        "message": f"job_id={job.id}",
                        "time": self._dt(job.started_at),
                        "sort_time": job.started_at,
                    }
                )

            if job.finished_at:
                timeline.append(
                    {
                        "type": "JOB_FINISHED",
                        "title": "执行任务已结束",
                        "status": self._value(job.status),
                        "message": job.error_message or f"job_id={job.id}",
                        "time": self._dt(job.finished_at),
                        "sort_time": job.finished_at,
                    }
                )

        for action in actions:
            timeline.append(
                {
                    "type": "ACTION",
                    "title": action.skill_name or action.action_name,
                    "status": self._value(action.status),
                    "message": action.error_message
                    or self._extract_action_message(action),
                    "time": self._dt(action.finished_at or action.started_at),
                    "sort_time": action.finished_at or action.started_at,
                    "duration_ms": self._duration_ms(
                        action.started_at,
                        action.finished_at,
                    ),
                    "sequence": action.sequence,
                    "skill_name": action.skill_name,
                    "action_name": action.action_name,
                }
            )

        timeline.sort(
            key=lambda item: item.get("sort_time") or datetime.min,
        )

        for item in timeline:
            item.pop("sort_time", None)

        return timeline

    @staticmethod
    def _serialize_task(task) -> dict[str, Any]:
        return {
            "id": task.id,
            "title": task.title,
            "task_type": TaskExecutionViewService._value(task.task_type),
            "source_type": TaskExecutionViewService._value(task.source_type),
            "source_chat_id": task.source_chat_id,
            "source_message_id": task.source_message_id,
            "status_card_message_id": getattr(task, "status_card_message_id", None),
            "execution_card_message_id": getattr(task, "execution_card_message_id", None),
            "creator_id": task.creator_id,
            "confirmed_by": getattr(task, "confirmed_by", None),
            "confirmed_at": TaskExecutionViewService._dt(
                getattr(task, "confirmed_at", None)
            ),
            "status": TaskExecutionViewService._value(task.status),
            "progress": task.progress,
            "current_step": task.current_step,
            "plan_json": task.plan_json,
            "created_at": TaskExecutionViewService._dt(task.created_at),
            "updated_at": TaskExecutionViewService._dt(task.updated_at),
        }

    @staticmethod
    def _serialize_artifact(artifact) -> dict[str, Any]:
        return {
            "id": artifact.id,
            "task_id": artifact.task_id,
            "artifact_type": artifact.artifact_type,
            "title": artifact.title,
            "status": artifact.status,
            "revision": artifact.revision,
            "source_action_id": artifact.source_action_id,
            "last_edited_by": artifact.last_edited_by,
            "reviewed_by": artifact.reviewed_by,
            "reviewed_at": TaskExecutionViewService._dt(artifact.reviewed_at),
            "feedback_text": artifact.feedback_text,
            "created_at": TaskExecutionViewService._dt(artifact.created_at),
            "updated_at": TaskExecutionViewService._dt(artifact.updated_at),
        }

    @staticmethod
    def _serialize_job(job) -> dict[str, Any]:
        return {
            "id": job.id,
            "task_id": job.task_id,
            "job_type": TaskExecutionViewService._value(job.job_type),
            "status": TaskExecutionViewService._value(job.status),
            "idempotency_key": job.idempotency_key,
            "retry_count": job.retry_count,
            "max_retries": job.max_retries,
            "error_message": job.error_message,
            "created_at": TaskExecutionViewService._dt(job.created_at),
            "updated_at": TaskExecutionViewService._dt(job.updated_at),
            "started_at": TaskExecutionViewService._dt(job.started_at),
            "finished_at": TaskExecutionViewService._dt(job.finished_at),
            "duration_ms": TaskExecutionViewService._duration_ms(
                job.started_at,
                job.finished_at,
            ),
        }

    @staticmethod
    def _serialize_action(action) -> dict[str, Any]:
        return {
            "id": action.id,
            "task_id": action.task_id,
            "sequence": action.sequence,
            "action_name": action.action_name,
            "skill_name": action.skill_name,
            "status": TaskExecutionViewService._value(action.status),
            "input_json": action.input_json,
            "output_json": action.output_json,
            "error_message": action.error_message,
            "started_at": TaskExecutionViewService._dt(action.started_at),
            "finished_at": TaskExecutionViewService._dt(action.finished_at),
            "duration_ms": TaskExecutionViewService._duration_ms(
                action.started_at,
                action.finished_at,
            ),
        }

    @staticmethod
    def _extract_delivery_result(actions: list) -> dict[str, Any]:
        delivery_result: dict[str, Any] = {}

        for action in actions:
            if action.skill_name != "delivery.prepare_result":
                continue

            if not action.output_json:
                continue

            data = action.output_json.get("data") or {}

            if isinstance(data, dict):
                delivery_result.update(data)

        return delivery_result

    @staticmethod
    def _extract_action_message(action) -> str:
        if not action.output_json:
            return ""

        message = action.output_json.get("message")

        if message:
            return str(message)

        data = action.output_json.get("data")

        if isinstance(data, dict):
            for key in ["message", "title", "doc_url", "slide_url", "url"]:
                if data.get(key):
                    return str(data[key])

        return ""

    @staticmethod
    def _latest_error(
        task_model,
        latest_job,
        actions: list,
    ) -> str | None:
        if latest_job is not None and latest_job.error_message:
            return latest_job.error_message

        for action in reversed(actions):
            if action.error_message:
                return action.error_message

        return None

    @staticmethod
    def _dt(value) -> str | None:
        if value is None:
            return None

        return value.isoformat()

    @staticmethod
    def _duration_ms(started_at, finished_at) -> int | None:
        if not started_at or not finished_at:
            return None

        return int((finished_at - started_at).total_seconds() * 1000)

    @staticmethod
    def _value(value) -> str | None:
        if value is None:
            return None

        if hasattr(value, "value"):
            return str(value.value)

        return str(value)
