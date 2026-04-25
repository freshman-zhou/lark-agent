from sqlalchemy.orm import Session

from packages.application.task_service import TaskService
from packages.integrations.feishu.auth.signature_verify import verify_verification_token
from packages.integrations.feishu.card.card_builder import CardBuilder
from packages.integrations.feishu.event.feishu_event_dto import FeishuMessageEventDTO
from packages.integrations.feishu.event.webhook_event_normalizer import WebhookEventNormalizer
from packages.integrations.feishu.im.event_parser import FeishuEventParser
from packages.integrations.feishu.im.message_api import FeishuMessageApi
from packages.shared.logger import get_logger

logger = get_logger(__name__)


class FeishuEventService:
    """飞书事件应用服务。

    Webhook 和长连接只是入口不同。
    进入业务层后统一处理 FeishuMessageEventDTO。
    """

    def __init__(self, db: Session):
        self.db = db
        self.parser = FeishuEventParser()
        self.webhook_normalizer = WebhookEventNormalizer()
        self.message_api = FeishuMessageApi()
        self.task_service = TaskService(db)

    async def handle_webhook_payload(self, payload: dict) -> dict:
        """HTTP Webhook 入口使用。"""
        if self.parser.is_url_verification(payload):
            logger.info("Feishu URL verification received")
            return {"challenge": payload.get("challenge")}

        if not verify_verification_token(payload):
            logger.warning("Invalid Feishu verification token")
            return {"code": 403, "message": "invalid verification token"}

        event = self.webhook_normalizer.normalize(payload)
        if event is None:
            logger.info("Ignored unsupported Feishu webhook event")
            return {"code": 0, "message": "ignored"}

        return await self.handle_message_event(event)

    async def handle_message_event(self, event: FeishuMessageEventDTO) -> dict:
        """Webhook 和长连接统一调用这个方法。"""
        logger.info(
            "Received Feishu message: event_type=%s chat_id=%s message_id=%s content=%s",
            event.event_type,
            event.chat_id,
            event.message_id,
            event.content,
        )

        if not event.content:
            await self.message_api.reply_text(
                event.message_id,
                "我收到了消息，但没有识别到有效文本内容。",
            )
            return {"code": 0, "message": "empty content"}

        task = self.task_service.create_from_feishu_message(
            content=event.content,
            chat_id=event.chat_id,
            message_id=event.message_id,
            creator_id=event.sender_id,
        )

        steps = []
        if task.plan_json:
            steps = [step["name"] for step in task.plan_json.get("steps", [])]

        reply = CardBuilder.task_created_text(
            task_id=task.id,
            title=task.title,
            task_type=task.task_type,
            steps=steps,
        )

        await self.message_api.reply_text(event.message_id, reply)

        return {
            "code": 0,
            "message": "ok",
            "task_id": task.id,
        }

    async def handle_event(self, payload: dict) -> dict:
        """兼容旧代码。"""
        return await self.handle_webhook_payload(payload)