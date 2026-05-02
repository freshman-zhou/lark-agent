import time
from typing import Any

from sqlalchemy.orm import Session

from packages.application.task_execution_view_service import TaskExecutionViewService
from packages.infrastructure.db.repositories.task_repository import TaskRepository
from packages.integrations.feishu.card.task_status_card import TaskStatusCard
from packages.integrations.feishu.im.message_api import FeishuMessageApi
from packages.shared.logger import get_logger


logger = get_logger(__name__)


class TaskCardRefreshService:
    """
    刷新任务状态卡片。

    注意：
    1. 这里读取 DB 中的 tasks / task_jobs / agent_actions；
    2. 不直接依赖 LangGraph 内部对象；
    3. 支持轻量节流，避免 LangGraph 节点频繁更新时过度请求飞书 API。
    """

    _last_refresh_at: dict[str, float] = {}

    def __init__(
        self,
        db: Session,
        min_interval_seconds: float = 1.0,
    ):
        self.db = db
        self.min_interval_seconds = min_interval_seconds
        self.task_repository = TaskRepository(db)
        self.execution_view_service = TaskExecutionViewService(db)
        self.message_api = FeishuMessageApi()

    async def create_execution_card_once(
        self,
        task_id: str,
        chat_id: str | None = None,
        force_refresh_if_exists: bool = True,
    ) -> dict[str, Any] | None:
        """
        确认任务后调用。

        如果 execution_card_message_id 已存在，不再创建新卡片，只刷新已有卡片。
        如果不存在，则向群聊发送一张新的任务执行状态卡片，并保存 message_id。
        """
        detail = self.execution_view_service.get_execution_detail(task_id)
        task = detail["task"]

        existing_message_id = task.get("execution_card_message_id")

        if existing_message_id:
            if force_refresh_if_exists:
                return await self.refresh_execution_card_by_task_id(
                    task_id=task_id,
                    force=True,
                )
            return None

        target_chat_id = chat_id or task.get("source_chat_id")

        if not target_chat_id:
            logger.info(
                "Skip create execution card because chat_id is empty: task_id=%s",
                task_id,
            )
            return None

        card = self._build_card_from_detail(detail)

        response = await self.message_api.send_card_to_chat(
            chat_id=target_chat_id,
            card=card,
        )

        message_id = FeishuMessageApi.extract_message_id(response)

        if message_id:
            self.task_repository.update_execution_card_message_id(
                task_id=task_id,
                execution_card_message_id=message_id,
            )

        return response

    async def refresh_execution_card_by_task_id(
        self,
        task_id: str,
        force: bool = False,
        checkpoint_next: list[str] | None = None,
    ) -> dict[str, Any] | None:
        """
        后续状态变化调用。

        注意：
        - 只更新已有 execution_card_message_id；
        - 如果没有执行卡片，直接跳过，不创建新卡片。
        """
        if not force and self._should_skip(task_id):
            return None

        detail = self.execution_view_service.get_execution_detail(task_id)
        task = detail["task"]

        message_id = task.get("execution_card_message_id")

        if not message_id:
            logger.info(
                "Skip refresh execution card because execution_card_message_id is empty: %s",
                task_id,
            )
            return None

        card = self._build_card_from_detail(
            detail=detail,
            checkpoint_next=checkpoint_next,
        )

        try:
            response = await self.message_api.update_card_message(
                message_id=message_id,
                card=card,
            )

            self._last_refresh_at[task_id] = time.time()

            return response

        except Exception as exc:
            logger.exception(
                "Failed to refresh execution card: task_id=%s message_id=%s error=%s",
                task_id,
                message_id,
                exc,
            )
            return None
        
    def _build_card_from_detail(
        self,
        detail: dict[str, Any],
        checkpoint_next: list[str] | None = None,
    ) -> dict:
        task = detail["task"]
        summary = detail["summary"]
        latest_job = detail.get("latest_job")
        actions = detail.get("actions") or []
        delivery_result = detail.get("delivery_result") or {}

        return TaskStatusCard.build(
            task_id=task["id"],
            title=task["title"],
            task_type=task["task_type"],
            status=task["status"],
            current_step=task["current_step"],
            confirmed_by=task.get("confirmed_by"),
            confirmed_at=task.get("confirmed_at"),
            latest_job=latest_job,
            actions=actions,
            delivery_result=delivery_result,
            error_message=summary.get("latest_error"),
            checkpoint_next=checkpoint_next,
        )

    async def refresh_by_task_id(
        self,
        task_id: str,
        fallback_message_id: str | None = None,
        force: bool = False,
        checkpoint_next: list[str] | None = None,
    ) -> dict[str, Any] | None:
        if not force and self._should_skip(task_id):
            return None

        detail = self.execution_view_service.get_execution_detail(task_id)

        task = detail["task"]
        summary = detail["summary"]
        latest_job = detail.get("latest_job")
        actions = detail.get("actions") or []
        delivery_result = detail.get("delivery_result") or {}

        message_id = task.get("status_card_message_id") or fallback_message_id

        if not message_id:
            logger.info(
                "Skip refresh task card because status_card_message_id is empty: %s",
                task_id,
            )
            return None

        if not task.get("status_card_message_id") and fallback_message_id:
            self.task_repository.update_status_card_message_id(
                task_id=task_id,
                status_card_message_id=fallback_message_id,
            )

        card = TaskStatusCard.build(
            task_id=task["id"],
            title=task["title"],
            task_type=task["task_type"],
            status=task["status"],
            current_step=task["current_step"],
            progress=task["progress"],
            confirmed_by=task.get("confirmed_by"),
            confirmed_at=task.get("confirmed_at"),
            latest_job=latest_job,
            actions=actions,
            delivery_result=delivery_result,
            error_message=summary.get("latest_error"),
            checkpoint_next=checkpoint_next,
        )

        try:
            result = await self.message_api.update_card_message(
                message_id=message_id,
                card=card,
            )

            self._last_refresh_at[task_id] = time.time()

            return result

        except Exception as exc:
            logger.exception(
                "Failed to refresh task card: task_id=%s message_id=%s error=%s",
                task_id,
                message_id,
                exc,
            )
            return None

    def _should_skip(self, task_id: str) -> bool:
        last = self._last_refresh_at.get(task_id)

        if last is None:
            return False

        return time.time() - last < self.min_interval_seconds