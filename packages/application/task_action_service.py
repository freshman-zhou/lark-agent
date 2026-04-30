from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from packages.application.agent_run_service import AgentRunService
from packages.agent.runtime.agent_runtime import AgentRuntime
from packages.domain.task.task_status import TaskJobStatus, TaskStatus
from packages.infrastructure.db.repositories.agent_action_repository import AgentActionRepository
from packages.infrastructure.db.repositories.task_repository import TaskRepository
from packages.infrastructure.db.repositories.task_job_repository import TaskJobRepository
from packages.shared.exceptions import TaskNotFoundException, TaskStatusException


class TaskActionService:
    def __init__(self, db: Session):
        self.db = db
        self.task_repository = TaskRepository(db)
        self.action_repository = AgentActionRepository(db)
        self.runtime = AgentRuntime(db)
        self.agent_run_service = AgentRunService()
        self.task_job_repository = TaskJobRepository(db)

    async def confirm_and_start(self, task_id: str,confirmed_by: str | None = None) -> dict:
        try:
            # 先确认任务存在。不存在时沿用原来的异常语义。
            self.task_repository.get_by_id(task_id)

            confirmed = self.task_repository.confirm_to_queued(
                task_id=task_id,
                confirmed_by=confirmed_by,
            )

            if not confirmed:
                self.db.rollback()

                current_task = self.task_repository.get_by_id(task_id)
                current_status = self._normalize_status(current_task.status)

                if current_status == TaskStatus.QUEUED:
                    return {
                        "task_id": task_id,
                        "status": current_status.value,
                        "message": "该任务已被确认，正在排队执行，无需重复确认",
                    }

                if current_status == TaskStatus.RUNNING:
                    return {
                        "task_id": task_id,
                        "status": current_status.value,
                        "message": "该任务正在执行中，无需重复确认",
                    }

                if current_status == TaskStatus.COMPLETED:
                    return {
                        "task_id": task_id,
                        "status": current_status.value,
                        "message": "该任务已经完成，无需重复确认",
                    }

                if current_status == TaskStatus.CANCELLED:
                    return {
                        "task_id": task_id,
                        "status": current_status.value,
                        "message": "该任务已取消，无法确认执行",
                    }

                raise TaskStatusException(
                    message=f"当前任务状态不允许确认执行：{current_status.value}",
                    detail={
                        "task_id": task_id,
                        "status": current_status.value,
                    },
                )

            self.task_job_repository.create_pending_langgraph_job(task_id=task_id)

            self.db.commit()

            return {
                "task_id": task_id,
                "status": TaskStatus.QUEUED.value,
                "job_status": TaskJobStatus.PENDING.value,
                "message": "任务已确认，已进入执行队列",
            }

        except IntegrityError:
            self.db.rollback()

            # idempotency_key 唯一索引兜底。
            current_task = self.task_repository.get_by_id(task_id)
            current_status = self._normalize_status(current_task.status)

            return {
                "task_id": task_id,
                "status": current_status.value,
                "message": "该任务已被确认并创建执行任务，无需重复操作",
            }


    async def confirm_and_run(
            self, 
            task_id: str,
            confirmed_by: str | None = None,
        ) -> dict:
        """兼容旧代码。后续统一使用 confirm_and_start。"""
        return await self.confirm_and_start(task_id,
            confirmed_by=confirmed_by)

    def cancel(self, task_id: str) -> dict:
        task = self.task_repository.get_by_id(task_id)

        if task is None:
            raise TaskNotFoundException(task_id)

        task_status = self._normalize_status(task.status)

        if task_status in {TaskStatus.COMPLETED, TaskStatus.CANCELLED}:
            return {
                "task_id": task_id,
                "status": task_status.value,
                "message": "任务已结束，无法取消",
            }

        self.task_repository.update_status(
            task_id=task_id,
            status=TaskStatus.CANCELLED,
            current_step="任务已取消",
            progress=0,
        )

        return {
            "task_id": task_id,
            "status": TaskStatus.CANCELLED.value,
            "message": "任务已取消",
            }

    def list_actions(self, task_id: str) -> list[dict]:
        task = self.task_repository.get_by_id(task_id)

        if task is None:
            raise TaskNotFoundException(task_id)

        actions = self.action_repository.list_by_task(task_id)

        return [
            {
                "id": action.id,
                "task_id": action.task_id,
                "sequence": action.sequence,
                "action_name": action.action_name,
                "skill_name": action.skill_name,
                "status": action.status,
                "input_json": action.input_json,
                "output_json": action.output_json,
                "error_message": action.error_message,
                "started_at": action.started_at.isoformat()
                if action.started_at
                else None,
                "finished_at": action.finished_at.isoformat()
                if action.finished_at
                else None,
            }
            for action in actions
        ]

    @staticmethod
    def _normalize_status(status: TaskStatus | str) -> TaskStatus:
        if isinstance(status, TaskStatus):
            return status
        return TaskStatus(status)
