# packages/application/feishu_event_service.py

from sqlalchemy.orm import Session

from packages.application.message_triage_service import (
    MessageIntent,
    MessageTriageService,
)
from packages.application.task_communication_service import TaskCommunicationService
from packages.application.task_preview_service import TaskPreviewService
from packages.infrastructure.db.repositories.processed_event_repository import (
    ProcessedEventRepository,
)
from packages.integrations.feishu.auth.signature_verify import verify_verification_token
from packages.integrations.feishu.event.feishu_event_dto import FeishuMessageEventDTO
from packages.integrations.feishu.event.webhook_event_normalizer import (
    WebhookEventNormalizer,
)
from packages.integrations.feishu.im.event_parser import FeishuEventParser
from packages.integrations.feishu.im.message_api import FeishuMessageApi
from packages.passive_listener.service import PassiveListenerService
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
        self.processed_event_repository = ProcessedEventRepository(db)
        self.passive_listener_service = PassiveListenerService(db)

    async def handle_message_event(
        self,
        event: FeishuMessageEventDTO,
    ) -> dict:
        processed_event, created = self.processed_event_repository.begin_message_event(
            event
        )

        if not created:
            logger.info(
                "Skip duplicate Feishu message event: event_id=%s message_id=%s "
                "processed_event_id=%s status=%s task_id=%s",
                event.event_id,
                event.message_id,
                processed_event.id,
                processed_event.status,
                processed_event.result_task_id,
            )

            return {
                "code": 0,
                "message": "duplicate_event_ignored",
                "event_id": event.event_id,
                "message_id": event.message_id,
                "processed_event_id": processed_event.id,
                "processed_status": processed_event.status,
                "task_id": processed_event.result_task_id,
            }

        try:
            result = await self._handle_claimed_message_event(event)

            if result.get("event_handling_status") == "IGNORED":
                self.processed_event_repository.mark_ignored(
                    processed_event.id,
                    result_message=result.get("message"),
                )
            else:
                self.processed_event_repository.mark_success(
                    processed_event.id,
                    result_task_id=result.get("task_id"),
                    result_message=result.get("message"),
                )

            return result

        except Exception as exc:
            self.processed_event_repository.mark_failed(
                processed_event.id,
                error_message=str(exc),
            )
            raise

    async def _handle_claimed_message_event(
        self,
        event: FeishuMessageEventDTO,
    ) -> dict:
        context_messages = self._build_recent_chat_context(event)
        triage = self.triage_service.triage_feishu_message(
            event,
            context_messages=context_messages,
        )

        logger.info(
            "Handle Feishu message event: chat_id=%s message_id=%s "
            "sender_id=%s mention_bot=%s intent=%s task_id=%s command=%s",
            event.chat_id,
            event.message_id,
            event.sender_id,
            event.is_mention_bot,
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
                "event_handling_status": "IGNORED",
            }

        if triage.intent == MessageIntent.PASSIVE_LISTEN:
            passive_result = self._capture_passive_message(
                event=event,
                triage=triage,
            )

            logger.info(
                "Passive listen candidate captured: chat_id=%s message_id=%s "
                "reason=%s passive_result=%s text=%s",
                event.chat_id,
                event.message_id,
                triage.reason,
                passive_result,
                triage.normalized_text,
            )

            return {
                "code": 0,
                "message": "passive_listen_captured",
                "reason": triage.reason,
                "passive_result": passive_result,
                "event_handling_status": "IGNORED",
            }

        if triage.intent == MessageIntent.NEED_CLARIFICATION:
            await self.message_api.reply_text(
                message_id=event.message_id,
                text=self._build_clarification_text(triage),
            )

            return {
                "code": 0,
                "message": "clarification_requested",
                "reason": triage.reason,
                "confidence": triage.confidence,
                "clarifying_questions": triage.clarifying_questions or [],
                "event_handling_status": "IGNORED",
            }

        if triage.intent == MessageIntent.CHAT:
            reply_text = await self._build_chat_reply(
                event=event,
                triage=triage,
                context_messages=context_messages,
            )
            await self.message_api.reply_text(
                message_id=event.message_id,
                text=reply_text,
            )

            return {
                "code": 0,
                "message": "chat_replied",
                "reason": triage.reason,
                "confidence": triage.confidence,
                "event_handling_status": "IGNORED",
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

        if triage.intent in {
            MessageIntent.EXPLICIT_NEW_TASK,
            MessageIntent.NEW_TASK_REQUEST,
        }:
            return await self.preview_service.create_preview_from_feishu_message(
                event=event,
                command=triage.normalized_text,
            )

        if not event.is_mention_bot:
            passive_result = self._capture_passive_message(
                event=event,
                triage=triage,
            )

            return {
                "code": 0,
                "message": "ignored",
                "reason": "message did not explicitly mention bot",
                "passive_result": passive_result,
                "event_handling_status": "IGNORED",
            }

        reply_text = await self._build_chat_reply(
            event=event,
            triage=triage,
            context_messages=context_messages,
        )
        await self.message_api.reply_text(
            message_id=event.message_id,
            text=reply_text,
        )

        return {
            "code": 0,
            "message": "unknown_replied",
            "command": triage.normalized_text,
            "event_handling_status": "IGNORED",
        }

    @staticmethod
    def _build_clarification_text(triage) -> str:
        questions = triage.clarifying_questions or [
            "你希望我输出文档、PPT，还是只做讨论摘要？"
        ]

        question_text = "\n".join([f"- {question}" for question in questions])

        return (
            "我理解你可能想让我推进一个任务，但还差一点信息：\n"
            f"{question_text}"
        )

    async def _build_chat_reply(
        self,
        *,
        event: FeishuMessageEventDTO,
        triage,
        context_messages: list[dict],
    ) -> str:
        try:
            from packages.agent.intent.explicit_chat_responder import (
                ExplicitChatResponder,
            )

            responder = ExplicitChatResponder()
            return await responder.reply(
                text=triage.normalized_text or event.content,
                context_messages=context_messages,
                reason=triage.reason,
            )

        except Exception as exc:
            logger.exception(
                "Explicit chat responder failed: chat_id=%s message_id=%s",
                event.chat_id,
                event.message_id,
            )
            return (
                "我在。这个看起来不像一个需要我立刻创建的任务。\n"
                "如果你希望我继续推进，可以直接说：帮我整理成文档、生成 PPT，或者总结一下刚才讨论。"
            )

    def _build_recent_chat_context(
        self,
        event: FeishuMessageEventDTO,
    ) -> list[dict]:
        if not event.chat_id:
            return []

        try:
            limit = self.triage_service.settings.explicit_chat_context_messages
            messages = self.passive_listener_service.repository.list_recent_messages(
                chat_id=event.chat_id,
                window_minutes=self.triage_service.settings.passive_listener_window_minutes,
                limit=limit,
            )

            return [
                {
                    "message_id": message.message_id,
                    "sender_id": message.sender_id,
                    "content": message.content,
                    "created_at": message.created_at.isoformat()
                    if message.created_at
                    else None,
                    "signal_score": message.signal_score,
                }
                for message in messages
                if message.message_id != event.message_id
            ]

        except Exception:
            logger.exception(
                "Failed to build recent chat context: chat_id=%s",
                event.chat_id,
            )
            return []

    def _capture_passive_message(
        self,
        *,
        event: FeishuMessageEventDTO,
        triage,
    ) -> dict:
        try:
            return self.passive_listener_service.capture_message(
                event=event,
                triage=triage,
            )
        except Exception as exc:
            logger.exception(
                "Passive listener capture failed: chat_id=%s message_id=%s",
                event.chat_id,
                event.message_id,
            )

            return {
                "captured": False,
                "reason": f"passive listener error: {exc}",
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
