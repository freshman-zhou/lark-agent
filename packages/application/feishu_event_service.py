# packages/application/feishu_event_service.py

from sqlalchemy.orm import Session

from packages.application.message_triage_service import (
    MessageIntent,
    MessageTriageService,
)
from packages.application.task_communication_service import TaskCommunicationService
from packages.application.task_preview_service import TaskPreviewService
from packages.integrations.feishu.auth.signature_verify import verify_verification_token
from packages.integrations.feishu.event.feishu_event_dto import FeishuMessageEventDTO
from packages.integrations.feishu.event.webhook_event_normalizer import (
    WebhookEventNormalizer,
)
from packages.integrations.feishu.im.event_parser import FeishuEventParser
from packages.integrations.feishu.im.message_api import FeishuMessageApi
from packages.shared.logger import get_logger


logger = get_logger(__name__)


class FeishuEventService:
    """
    飞书事件业务服务。

    重构后职责变薄：
    1. 接收标准化后的飞书消息事件；
    2. 调用 MessageTriageService 判断消息类型；
    3. 根据意图分发给预览层或沟通层；
    4. 不直接创建任务，不直接确认任务，不直接执行 Agent。
    """

    def __init__(self, db: Session):
        self.db = db

        self.parser = FeishuEventParser()
        self.webhook_normalizer = WebhookEventNormalizer()
        self.message_api = FeishuMessageApi()

        self.triage_service = MessageTriageService()
        self.preview_service = TaskPreviewService(db)
        self.communication_service = TaskCommunicationService(db)

    async def handle_message_event(
        self,
        event: FeishuMessageEventDTO,
    ) -> dict:
        triage = self.triage_service.triage_feishu_message(event)

        logger.info(
            "Handle Feishu message event: chat_id=%s message_id=%s "
            "sender_id=%s intent=%s task_id=%s command=%s",
            event.chat_id,
            event.message_id,
            event.sender_id,
            triage.intent,
            triage.task_id,
            triage.normalized_text,
        )

        if triage.intent == MessageIntent.EMPTY:
            await self.message_api.reply_text(
                message_id=event.message_id,
                text=(
                    "我收到了消息，但没有识别到有效指令。\n"
                    "你可以说：帮我把刚才讨论整理成方案文档。"
                ),
            )

            return {
                "code": 0,
                "message": "empty command",
            }

        if triage.intent == MessageIntent.IGNORE:
            return {
                "code": 0,
                "message": "ignored",
                "reason": triage.reason,
            }

        if triage.intent == MessageIntent.CONFIRM_TASK:
            return await self.communication_service.confirm_task(
                task_id=triage.task_id,
                confirmed_by=event.sender_id,
                chat_id=event.chat_id,
                reply_message_id=event.message_id,
            )

        if triage.intent == MessageIntent.CANCEL_TASK:
            return await self.communication_service.cancel_task(
                task_id=triage.task_id,
                reply_message_id=event.message_id,
            )

        if triage.intent == MessageIntent.CLARIFY_REPLY:
            return await self.communication_service.handle_clarify_reply(
                task_id=triage.task_id,
                text=triage.normalized_text,
                reply_message_id=event.message_id,
            )

        if triage.intent == MessageIntent.NEW_TASK_REQUEST:
            return await self.preview_service.create_preview_from_feishu_message(
                event=event,
                command=triage.normalized_text,
            )

        await self.message_api.reply_text(
            message_id=event.message_id,
            text=(
                "我还没有识别出你的任务意图。\n"
                "你可以这样说：帮我把刚才讨论整理成方案文档。"
            ),
        )

        return {
            "code": 0,
            "message": "unknown command",
            "command": triage.normalized_text,
        }

    async def handle_webhook_payload(self, payload: dict) -> dict:
        """
        保留 Webhook 入口，长连接阶段可以暂时不用。
        """
        if self.parser.is_url_verification(payload):
            return {
                "challenge": payload.get("challenge"),
            }

        if not verify_verification_token(payload):
            logger.warning("Invalid Feishu verification token")

            return {
                "code": 403,
                "message": "invalid verification token",
            }

        event = self.webhook_normalizer.normalize(payload)

        if event is None:
            return {
                "code": 0,
                "message": "ignored",
            }

        return await self.handle_message_event(event)

    async def handle_event(self, payload: dict) -> dict:
        """
        兼容旧代码。
        """
        return await self.handle_webhook_payload(payload)