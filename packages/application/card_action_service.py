from sqlalchemy.orm import Session

from packages.application.task_action_service import TaskActionService
from packages.application.task_card_refresh_service import TaskCardRefreshService
from packages.integrations.feishu.event.card_action_normalizer import FeishuCardActionDTO
from packages.shared.logger import get_logger


logger = get_logger(__name__)


class CardActionService:
    def __init__(self, db: Session):
        self.db = db
        self.task_action_service = TaskActionService(db)
        self.card_refresh_service = TaskCardRefreshService(db)

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
            result = await self.task_action_service.confirm_and_start(
                task_id=dto.task_id,
                confirmed_by=dto.operator_id,
            )

            # 只在确认后创建一张新的执行状态卡片。
            # 如果已存在，则只刷新，不重复创建。
            await self.card_refresh_service.create_execution_card_once(
                task_id=dto.task_id,
                chat_id=dto.open_chat_id,
                force_refresh_if_exists=True,
            )

            return {
                "ok": True,
                "message": result.get("message") or "任务已确认，已创建执行状态卡片",
                "result": result,
            }

        if dto.action == "cancel_task":
            result = self.task_action_service.cancel(dto.task_id)

            # 取消时只尝试刷新已有执行卡片。
            # 如果没有执行卡片，不新建。
            await self.card_refresh_service.refresh_execution_card_by_task_id(
                task_id=dto.task_id,
                force=True,
            )

            return {
                "ok": True,
                "message": result.get("message") or "任务已取消",
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