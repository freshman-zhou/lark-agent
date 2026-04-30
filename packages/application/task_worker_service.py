import asyncio
import threading
from typing import Any

from packages.agent.graph.langgraph_task_runner import LangGraphTaskRunner
from packages.application.task_notify_service import TaskNotifyService
from packages.domain.task.task_status import TaskJobStatus, TaskStatus
from packages.infrastructure.db.database import SessionLocal
from packages.infrastructure.db.repositories.agent_action_repository import AgentActionRepository
from packages.infrastructure.db.repositories.task_job_repository import TaskJobRepository
from packages.infrastructure.db.repositories.task_repository import TaskRepository
from packages.shared.logger import get_logger

logger = get_logger(__name__)


class TaskWorkerService:
    """
    简单任务 worker。

    第一版使用进程内 daemon thread + 轮询数据库。
    后续可以替换为 Celery / RQ / Arq / 独立 worker 进程。
    """

    def __init__(self, poll_interval_seconds: float = 2.0):
        self.poll_interval_seconds = poll_interval_seconds
        self._thread: threading.Thread | None = None
        self._stop_event = threading.Event()

    def start_background(self) -> None:
        if self._thread is not None and self._thread.is_alive():
            return

        self._stop_event.clear()

        self._thread = threading.Thread(
            target=self._run_in_thread,
            name="task-worker-service",
            daemon=True,
        )
        self._thread.start()

        logger.info("TaskWorkerService started")

    def stop(self) -> None:
        self._stop_event.set()

        if self._thread is not None and self._thread.is_alive():
            self._thread.join(timeout=5)

        logger.info("TaskWorkerService stopped")

    def _run_in_thread(self) -> None:
        asyncio.run(self.run_forever())

    async def run_forever(self) -> None:
        while not self._stop_event.is_set():
            try:
                has_job = await self.run_once()

                if not has_job:
                    await asyncio.sleep(self.poll_interval_seconds)

            except Exception as exc:
                logger.exception("Task worker loop error: %s", exc)
                await asyncio.sleep(self.poll_interval_seconds)

    async def run_once(self) -> bool:
        db = SessionLocal()

        try:
            task_repository = TaskRepository(db)
            job_repository = TaskJobRepository(db)

            job = job_repository.claim_next_pending_job()

            if job is None:
                return False

            logger.info(
                "Task worker claimed job: job_id=%s task_id=%s",
                job.id,
                job.task_id,
            )

            task = task_repository.get_by_id(job.task_id)
            task_status = self._normalize_status(task.status)

            if task_status == TaskStatus.CANCELLED:
                job_repository.mark_failed(
                    job_id=job.id,
                    error_message="任务已取消，跳过执行",
                )
                return True

            marked_running = task_repository.mark_running_if_queued(job.task_id)

            if not marked_running:
                db.rollback()

                refreshed_task = task_repository.get_by_id(job.task_id)
                refreshed_status = self._normalize_status(refreshed_task.status)

                if refreshed_status == TaskStatus.RUNNING:
                    logger.info(
                        "Task already running: task_id=%s",
                        job.task_id,
                    )
                else:
                    job_repository.mark_failed(
                        job_id=job.id,
                        error_message=f"任务状态不允许执行：{refreshed_status.value}",
                    )

                return True

            db.commit()

            task = task_repository.get_by_id(job.task_id)

            notify_service = TaskNotifyService()

            if task.source_chat_id:
                await notify_service.send_progress_to_chat(
                    chat_id=task.source_chat_id,
                    task=task,
                )

            runner = LangGraphTaskRunner(db)
            runtime_result = await runner.run(job.task_id)

            db.commit()

            refreshed_task = task_repository.get_by_id(job.task_id)
            refreshed_status = self._normalize_status(refreshed_task.status)

            final_result = self._build_delivery_result(
                db=db,
                task_id=job.task_id,
                runtime_result=runtime_result,
            )

            if refreshed_status == TaskStatus.COMPLETED:
                job_repository.mark_success(job.id)

                if refreshed_task.source_chat_id:
                    await notify_service.send_result_to_chat(
                        chat_id=refreshed_task.source_chat_id,
                        task=refreshed_task,
                        result=final_result,
                    )

                return True

            error_message = self._extract_runtime_error(runtime_result)

            retried_job = job_repository.mark_retrying_or_failed(
                job_id=job.id,
                error_message=error_message,
            )

            if retried_job.status == TaskJobStatus.PENDING.value:
                task_repository.update_status(
                    task_id=job.task_id,
                    status=TaskStatus.QUEUED,
                    current_step=f"执行失败，等待重试：{error_message}",
                    progress=5,
                    error_message=error_message,
                )
            else:
                task_repository.update_status(
                    task_id=job.task_id,
                    status=TaskStatus.FAILED,
                    current_step="任务执行失败",
                    progress=0,
                    error_message=error_message,
                )

                if refreshed_task.source_chat_id:
                    await notify_service.send_failed_to_chat(
                        chat_id=refreshed_task.source_chat_id,
                        task=refreshed_task,
                        error_message=error_message,
                    )

            return True

        except Exception as exc:
            logger.exception("Task worker run_once failed: %s", exc)

            try:
                db.rollback()
            except Exception:
                logger.exception("Task worker rollback failed")

            return False

        finally:
            db.close()

    @staticmethod
    def _build_delivery_result(
        db,
        task_id: str,
        runtime_result: dict[str, Any],
    ) -> dict[str, Any]:
        action_repository = AgentActionRepository(db)
        actions = action_repository.list_by_task(task_id)

        delivery_data: dict[str, Any] = {}

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
            return str(
                runtime_result.get("error")
                or runtime_result.get("message")
                or "未知错误"
            )

        return str(runtime_result or "未知错误")


task_worker_service = TaskWorkerService()