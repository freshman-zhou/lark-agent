# packages/application/task_preview_service.py

from sqlalchemy.orm import Session

from packages.application.task_notify_service import TaskNotifyService
from packages.application.task_service import TaskService
from packages.integrations.feishu.card.card_builder import CardBuilder
from packages.integrations.feishu.event.feishu_event_dto import FeishuMessageEventDTO
from packages.integrations.feishu.im.message_api import FeishuMessageApi
from packages.shared.logger import get_logger


logger = get_logger(__name__)


class TaskPreviewService:
    """
    任务预览服务。

    职责：
    1. 根据用户消息创建任务预览；
    2. 保存 WAITING_CONFIRM 状态任务；
    3. 发送任务预览卡片；
    4. 不确认任务，不启动执行，不创建执行状态卡片。
    """

    def __init__(self, db: Session):
        self.db = db
        self.task_service = TaskService(db)
        self.notify_service = TaskNotifyService()
        self.message_api = FeishuMessageApi()

    async def create_preview_from_feishu_message(
        self,
        event: FeishuMessageEventDTO,
        command: str,
    ) -> dict:
        task = self.task_service.create_preview_from_feishu_message(
            content=command,
            chat_id=event.chat_id,
            message_id=event.message_id,
            creator_id=event.sender_id,
        )

        try:
            await self.notify_service.send_preview_by_reply(
                message_id=event.message_id,
                task=task,
            )

            reply_type = "card"

        except Exception as exc:
            logger.exception(
                "Failed to send preview card, fallback to text: %s",
                exc,
            )

            preview = task.plan_json or {}

            reply_text = CardBuilder.task_preview_text(
                task_id=task.id,
                title=task.title,
                task_type=task.task_type,
                preview=preview,
            )

            await self.message_api.reply_text(
                message_id=event.message_id,
                text=reply_text,
            )

            reply_type = "text"

        return {
            "code": 0,
            "message": "preview_created",
            "task_id": task.id,
            "reply_type": reply_type,
        }