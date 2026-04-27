from sqlalchemy.orm import Session

from packages.application.agent_run_service import AgentRunService
from packages.agent.runtime.agent_runtime import AgentRuntime
from packages.domain.task.task_status import TaskStatus
from packages.infrastructure.db.repositories.agent_action_repository import AgentActionRepository
from packages.infrastructure.db.repositories.task_repository import TaskRepository
from packages.shared.exceptions import TaskNotFoundException, TaskStatusException


class TaskActionService:
    def __init__(self, db: Session):
        self.db = db
        self.task_repository = TaskRepository(db)
        self.action_repository = AgentActionRepository(db)
        self.runtime = AgentRuntime(db)
        self.agent_run_service = AgentRunService()

    async def confirm_and_start(self, task_id: str) -> dict:
        task = self.task_repository.get_by_id(task_id)

        if task is None:
            raise TaskNotFoundException(task_id)

        task_status = self._normalize_status(task.status)

        if task_status == TaskStatus.COMPLETED:
            return {
                "task_id": task_id,
                "status": task_status.value,
                "message": "任务已经完成，无需重复确认",
            }

        if task_status == TaskStatus.RUNNING:
            return {
                "task_id": task_id,
                "status": task_status.value,
                "message": "任务正在执行中，无需重复确认",
            }

        if task_status != TaskStatus.WAITING_CONFIRM:
            raise TaskStatusException(
                message=f"当前任务状态不允许确认执行：{task_status.value}",
                detail={
                    "task_id": task_id,
                    "status": task_status.value,
                },
            )

        self.task_repository.update_status(
            task_id=task_id,
            status=TaskStatus.CONFIRMED,
            current_step="用户已确认，准备启动 AgentRuntime",
            progress=5,
        )

        self.agent_run_service.start_background(task_id)

        return {
            "task_id": task_id,
            "status": TaskStatus.CONFIRMED.value,
            "message": "任务已确认，AgentRuntime 已开始后台执行",
        }

    async def confirm_and_run(self, task_id: str) -> dict:
        """兼容旧代码。后续统一使用 confirm_and_start。"""
        return await self.confirm_and_start(task_id)

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
