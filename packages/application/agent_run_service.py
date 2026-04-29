import asyncio
import threading
from typing import Any

from packages.agent.runtime.agent_runtime import AgentRuntime
from packages.domain.task.task_status import TaskStatus
from packages.infrastructure.db.database import SessionLocal
from packages.infrastructure.db.repositories.agent_action_repository import AgentActionRepository
from packages.infrastructure.db.repositories.task_repository import TaskRepository
from packages.application.task_notify_service import TaskNotifyService
from packages.shared.logger import get_logger

logger = get_logger(__name__)


class AgentRunService:
    """后台运行 AgentRuntime。

    当前版本使用 daemon thread 做 MVP。
    后续建议替换为 Celery / RQ / Arq。
    """

    def start_background(self, task_id: str) -> None:
        thread = threading.Thread(
            target=self._run_in_thread,
            args=(task_id,),
            daemon=True,
        )
        thread.start()

    def _run_in_thread(self, task_id: str) -> None:
        asyncio.run(self._run_task(task_id))

    async def _run_task(self, task_id: str) -> None:
        db = SessionLocal()

        try:
            task_repo = TaskRepository(db)
            notify_service = TaskNotifyService()
            runtime = AgentRuntime(db)

            task = task_repo.get_by_id(task_id)
            if task is None:
                logger.warning("Task not found when running background: %s", task_id)
                return

            if task.source_chat_id:
                await notify_service.send_progress_to_chat(
                    chat_id=task.source_chat_id,
                    task=task,
                )

            result = await runtime.run(task_id)

            db.commit()

            refreshed_task = task_repo.get_by_id(task_id)
            if refreshed_task is None:
                return

            final_result = self._build_delivery_result(db, task_id, result)

            refreshed_status = self._normalize_status(refreshed_task.status)

            if refreshed_status == TaskStatus.COMPLETED:
                if refreshed_task.source_chat_id:
                    await notify_service.send_result_to_chat(
                        chat_id=refreshed_task.source_chat_id,
                        task=refreshed_task,
                        result=final_result,
                    )

            elif refreshed_status == TaskStatus.FAILED:
                if refreshed_task.source_chat_id:
                    await notify_service.send_failed_to_chat(
                        chat_id=refreshed_task.source_chat_id,
                        task=refreshed_task,
                        error_message=self._extract_runtime_error(result),
                    )

        except Exception as exc:
            logger.exception("Background AgentRuntime failed: task_id=%s error=%s", task_id, exc)

            try:
                task_repo = TaskRepository(db)
                task = task_repo.get_by_id(task_id)
                if task is not None:
                    task_repo.update_status(
                        task_id=task_id,
                        status=TaskStatus.FAILED,
                        current_step="后台执行异常",
                        progress=0,
                        error_message=str(exc),
                    )

                    if task.source_chat_id:
                        notify_service = TaskNotifyService()
                        await notify_service.send_failed_to_chat(
                            chat_id=task.source_chat_id,
                            task=task,
                            error_message=str(exc),
                        )
            except Exception:
                logger.exception("Failed to update failed status for task=%s", task_id)

        finally:
            db.close()

    @staticmethod
    def _build_delivery_result(db, task_id: str, runtime_result: dict[str, Any]) -> dict[str, Any]:
        action_repo = AgentActionRepository(db)
        actions = action_repo.list_by_task(task_id)

        delivery_data = {}
        for action in actions:
            if action.skill_name == "delivery.prepare_result" and action.output_json:
                data = action.output_json.get("data") or {}
                if isinstance(data, dict):
                    delivery_data.update(data)

        return {
            **delivery_data,
            "task_id": task_id,
            "status": runtime_result.get("status"),
            "action_count": runtime_result.get("action_count"),
            "message": runtime_result.get("message", "任务执行完成"),
        }

    @staticmethod
    def _normalize_status(status: TaskStatus | str) -> TaskStatus:
        if isinstance(status, TaskStatus):
            return status
        return TaskStatus(status)

    @staticmethod
    def _extract_runtime_error(runtime_result: Any) -> str:
        if isinstance(runtime_result, dict):
            return str(runtime_result.get("error") or runtime_result.get("message") or "未知错误")
        return str(runtime_result or "未知错误")
