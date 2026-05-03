# packages/application/card_action_service.py

from sqlalchemy.orm import Session

from packages.application.task_communication_service import TaskCommunicationService
from packages.integrations.feishu.event.card_action_normalizer import FeishuCardActionDTO
from packages.shared.logger import get_logger


logger = get_logger(__name__)


class CardActionService:
    """
    卡片回调服务。

    重构后职责：
    1. 只负责接收卡片回调 DTO；
    2. 根据 action 分发给 TaskCommunicationService；
    3. 不直接操作 TaskActionService；
    4. 不更新预览卡片；
    5. 确认后创建一张独立的执行状态卡片。
    """

    def __init__(self, db: Session):
        self.db = db
        self.communication_service = TaskCommunicationService(db)

    async def handle_card_action(self, dto: FeishuCardActionDTO) -> dict:
        logger.info(
            "Handle card action: action=%s task_id=%s operator=%s chat_id=%s",
            dto.action,
            dto.task_id,
            dto.operator_id,
            dto.open_chat_id,
        )

        if not dto.action:
            return {
                "ok": False,
                "message": "缺少 action",
            }

        if not dto.task_id:
            return {
                "ok": False,
                "message": "缺少 task_id",
            }

        if dto.action == "confirm_task":
            result = await self.communication_service.confirm_task(
                task_id=dto.task_id,
                confirmed_by=dto.operator_id,
                chat_id=dto.open_chat_id,
                reply_message_id=None,
            )

            return {
                "ok": True,
                "message": "任务已确认，已创建执行状态卡片",
                "result": result,
            }

        if dto.action == "cancel_task":
            result = await self.communication_service.cancel_task(
                task_id=dto.task_id,
                reply_message_id=None,
            )

            return {
                "ok": True,
                "message": "任务已取消",
                "result": result,
            }

        if dto.action == "regenerate_preview":
            return {
                "ok": False,
                "message": "重新规划功能下一阶段实现",
            }

        return {
            "ok": False,
            "message": f"暂不支持的操作：{dto.action}",
        }