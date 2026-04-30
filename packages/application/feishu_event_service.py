import json
import re

from sqlalchemy.orm import Session

from packages.application.task_action_service import TaskActionService
from packages.application.task_notify_service import TaskNotifyService
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
    """飞书事件业务服务。

    长连接和 Webhook 都应该转成 FeishuMessageEventDTO 后进入这里。
    """

    def __init__(self, db: Session):
        self.db = db
        self.parser = FeishuEventParser()
        self.webhook_normalizer = WebhookEventNormalizer()
        self.task_service = TaskService(db)
        self.message_api = FeishuMessageApi()
        self.task_action_service = TaskActionService(db)
        self.notify_service = TaskNotifyService()
    
    #处理消息  理解消息识别意图并生成任务。  v1版本只做简单触发
    async def handle_message_event(self, event: FeishuMessageEventDTO) -> dict:
        command = self._normalize_message_content(event.content)

        logger.info(
            "Handle Feishu message event: chat_id=%s message_id=%s sender_id=%s command=%s",
            event.chat_id,
            event.message_id,
            event.sender_id,
            command,
        )

        if not command:
            await self.message_api.reply_text(
                message_id=event.message_id,
                text="我收到了消息，但没有识别到有效指令。你可以说：帮我把刚才讨论整理成方案文档。",
            )
            return {"code": 0, "message": "empty command"}

        #截取 确认/取消任务   保留做兜底
        confirm_task_id = self._extract_action_task_id(command, action="确认")
        if confirm_task_id:
            result = await self.task_action_service.confirm_and_run(
                task_id=confirm_task_id,
                confirmed_by=event.sender_id,
            )
            await self.message_api.reply_text(
                message_id=event.message_id,
                text=CardBuilder.runtime_result_text(result),
            )
            return {
                "code": 0,
                "message": "confirmed",
                "task_id": confirm_task_id,
                "runtime_result": result,
            }

        cancel_task_id = self._extract_action_task_id(command, action="取消")
        if cancel_task_id:
            result = self.task_action_service.cancel(cancel_task_id)
            await self.message_api.reply_text(
                message_id=event.message_id,
                text=f"任务已取消：{result.get('task_id')}",
            )
            return {
                "code": 0,
                "message": "cancelled",
                "task_id": cancel_task_id,
            }

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
        except Exception as exc:
            logger.exception("Failed to send preview card, fallback to text: %s", exc)

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

        return {
            "code": 0,
            "message": "preview_created",
            "task_id": task.id,
        }
    
    #保留webhook方式处理消息
    async def handle_webhook_payload(self, payload: dict) -> dict:
        """保留 Webhook 入口，长连接阶段可以暂时不用。"""

        if self.parser.is_url_verification(payload):
            return {"challenge": payload.get("challenge")}

        if not verify_verification_token(payload):
            logger.warning("Invalid Feishu verification token")
            return {"code": 403, "message": "invalid verification token"}

        event = self.webhook_normalizer.normalize(payload)

        if event is None:
            return {"code": 0, "message": "ignored"}

        return await self.handle_message_event(event)

    async def handle_event(self, payload: dict) -> dict:
        """兼容旧代码。"""
        return await self.handle_webhook_payload(payload)

    @staticmethod
    def _normalize_message_content(content: str) -> str:
        """兼容飞书 text content 是 JSON 字符串的情况。"""

        text = content or ""

        try:
            parsed = json.loads(text)
            if isinstance(parsed, dict):
                text = parsed.get("text") or parsed.get("content") or text
        except Exception:
            pass

        # 清理 at 标签
        text = re.sub(r"<at[^>]*>.*?</at>", "", text)
        text = re.sub(r"@\S+", "", text)

        text = text.replace("\u2005", " ")
        text = re.sub(r"\s+", " ", text)

        return text.strip()
    
    @staticmethod
    def _extract_action_task_id(command: str, action: str) -> str | None:
        pattern = rf"^\s*{re.escape(action)}\s*[:：]?\s*(task_[a-zA-Z0-9]+)\s*$"
        match = re.search(pattern, command)
        if not match:
            return None
        return match.group(1)
