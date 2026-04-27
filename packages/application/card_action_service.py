from sqlalchemy.orm import Session

from packages.application.task_action_service import TaskActionService
from packages.integrations.feishu.event.card_action_normalizer import FeishuCardActionDTO
from packages.shared.logger import get_logger

logger = get_logger(__name__)


class CardActionService:
    def __init__(self, db: Session):
        self.db = db
        self.task_action_service = TaskActionService(db)

    #根据卡片回传 触发相应动作
    async def handle_card_action(self, dto: FeishuCardActionDTO) -> dict:
        logger.info(
            "Handle card action: action=%s task_id=%s operator=%s",
            dto.action,
            dto.task_id,
            dto.operator_id,
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
            result = await self.task_action_service.confirm_and_start(dto.task_id)
            return {
                "ok": True,
                "message": "任务已确认，Agent 正在后台执行",
                "result": result,
            }

        if dto.action == "cancel_task":
            result = self.task_action_service.cancel(dto.task_id)
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