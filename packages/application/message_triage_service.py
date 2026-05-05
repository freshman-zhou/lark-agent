# packages/application/message_triage_service.py

import json
import re
from dataclasses import dataclass
from enum import Enum

from packages.integrations.feishu.event.feishu_event_dto import FeishuMessageEventDTO
from packages.shared.config import get_settings
from packages.shared.logger import get_logger


logger = get_logger(__name__)


class MessageIntent(str, Enum):
    EMPTY = "EMPTY"
    IGNORE = "IGNORE"
    CHAT = "CHAT"
    EXPLICIT_NEW_TASK = "EXPLICIT_NEW_TASK"
    PASSIVE_LISTEN = "PASSIVE_LISTEN"
    NEW_TASK_REQUEST = "NEW_TASK_REQUEST"
    CONFIRM_TASK = "CONFIRM_TASK"
    CANCEL_TASK = "CANCEL_TASK"
    CLARIFY_REPLY = "CLARIFY_REPLY"
    NEED_CLARIFICATION = "NEED_CLARIFICATION"
    UNKNOWN = "UNKNOWN"


@dataclass
class MessageTriageResult:
    intent: MessageIntent
    normalized_text: str
    task_id: str | None = None
    reason: str | None = None
    confidence: float | None = None
    task_type: str | None = None
    clarifying_questions: list[str] | None = None
    raw_intent: dict | None = None


class MessageTriageService:
    """
    群消息分诊服务。

    职责：
    1. 清洗飞书消息内容；
    2. 判断消息意图；
    3. 提取 task_id；
    4. 不创建任务，不执行任务，不发送卡片。
    """

    TASK_ID_PATTERN = r"(task_[a-zA-Z0-9_\-]+)"

    def __init__(self):
        self.settings = get_settings()
        self.explicit_intent_detector = None

    def triage_feishu_message(
        self,
        event: FeishuMessageEventDTO,
        context_messages: list[dict] | None = None,
    ) -> MessageTriageResult:
        text = self.normalize_message_content(event.content)

        return self.triage_text(
            text,
            is_explicit_trigger=event.is_mention_bot,
            message_type=event.message_type,
            context_messages=context_messages,
        )

    def triage_text(
        self,
        text: str,
        *,
        is_explicit_trigger: bool = True,
        message_type: str | None = "text",
        context_messages: list[dict] | None = None,
    ) -> MessageTriageResult:
        normalized_text = self.normalize_message_content(text)

        if not normalized_text:
            return MessageTriageResult(
                intent=MessageIntent.EMPTY,
                normalized_text="",
                reason="empty message",
            )

        if not self._is_text_like_message(message_type):
            return MessageTriageResult(
                intent=MessageIntent.IGNORE,
                normalized_text=normalized_text,
                reason=f"unsupported message type: {message_type}",
            )

        confirm_task_id = self.extract_action_task_id(
            normalized_text,
            actions=["确认", "执行", "开始", "确认执行"],
        )

        if confirm_task_id:
            return MessageTriageResult(
                intent=MessageIntent.CONFIRM_TASK,
                normalized_text=normalized_text,
                task_id=confirm_task_id,
                reason="matched confirm task command",
            )

        cancel_task_id = self.extract_action_task_id(
            normalized_text,
            actions=["取消", "停止", "终止", "取消任务"],
        )

        if cancel_task_id:
            return MessageTriageResult(
                intent=MessageIntent.CANCEL_TASK,
                normalized_text=normalized_text,
                task_id=cancel_task_id,
                reason="matched cancel task command",
            )

        if self._looks_like_clarify_reply(normalized_text):
            task_id = self.extract_any_task_id(normalized_text)

            return MessageTriageResult(
                intent=MessageIntent.CLARIFY_REPLY,
                normalized_text=normalized_text,
                task_id=task_id,
                reason="looks like clarification reply",
            )

        if self._looks_like_ignore(normalized_text):
            return MessageTriageResult(
                intent=MessageIntent.IGNORE,
                normalized_text=normalized_text,
                reason="looks like non-task message",
            )

        if is_explicit_trigger:
            return self._triage_explicit_mention(
                normalized_text,
                context_messages=context_messages,
            )

        if self._looks_like_new_task(normalized_text):
            return MessageTriageResult(
                intent=MessageIntent.PASSIVE_LISTEN,
                normalized_text=normalized_text,
                reason="task-like message without explicit bot mention",
            )

        return MessageTriageResult(
            intent=MessageIntent.UNKNOWN,
            normalized_text=normalized_text,
            reason="no rule matched",
        )

    @staticmethod
    def normalize_message_content(content: str) -> str:
        """
        兼容飞书 text content 是 JSON 字符串的情况。
        """
        text = content or ""

        try:
            parsed = json.loads(text)

            if isinstance(parsed, dict):
                text = (
                    parsed.get("text")
                    or parsed.get("content")
                    or parsed.get("message")
                    or text
                )
        except Exception:
            pass

        # 清理飞书 at 标签和特殊空格
        text = re.sub(r"<at[^>]*>.*?</at>", "", text)
        text = re.sub(r"<at[^>]*>", "", text)
        text = re.sub(r"@\S+", "", text)
        text = text.replace("\u2005", " ")
        text = re.sub(r"\s+", " ", text)

        return text.strip()

    def extract_action_task_id(
        self,
        command: str,
        actions: list[str],
    ) -> str | None:
        for action in actions:
            pattern = (
                rf"^\s*{re.escape(action)}\s*"
                rf"[:：]?\s*{self.TASK_ID_PATTERN}\s*$"
            )

            match = re.search(pattern, command)

            if match:
                return match.group(1)

        return None

    def extract_any_task_id(self, command: str) -> str | None:
        match = re.search(self.TASK_ID_PATTERN, command)

        if not match:
            return None

        return match.group(1)

    @staticmethod
    def _looks_like_new_task(text: str) -> bool:
        keywords = [
            "帮我",
            "生成",
            "整理",
            "总结",
            "汇总",
            "写",
            "创建",
            "输出",
            "做一个",
            "文档",
            "方案",
            "报告",
            "PPT",
            "ppt",
            "演示稿",
            "会议纪要",
            "群聊",
            "讨论",
            "刚才",
        ]

        return any(keyword in text for keyword in keywords)

    @staticmethod
    def _looks_like_clarify_reply(text: str) -> bool:
        keywords = [
            "补充",
            "改成",
            "改为",
            "标题",
            "范围",
            "不要",
            "需要",
            "再加",
            "删掉",
            "保留",
            "换成",
        ]

        return any(keyword in text for keyword in keywords) and "task_" in text

    @staticmethod
    def _looks_like_ignore(text: str) -> bool:
        ignore_texts = {
            "好的",
            "收到",
            "ok",
            "OK",
            "嗯",
            "是的",
            "不是",
            "谢谢",
            "不用了",
            "没事",
        }

        return text in ignore_texts

    @staticmethod
    def _is_text_like_message(message_type: str | None) -> bool:
        return (message_type or "").lower() in {"text", "post"}

    def _triage_explicit_mention(
        self,
        normalized_text: str,
        *,
        context_messages: list[dict] | None = None,
    ) -> MessageTriageResult:
        if not self.settings.explicit_intent_enable_llm:
            return self._fallback_explicit_mention(
                normalized_text,
                reason="explicit intent LLM disabled",
            )

        try:
            result = self._run_explicit_intent_detector(
                normalized_text,
                context_messages=context_messages,
            )
        except Exception as exc:
            logger.exception("Explicit intent detector failed, fallback to rules: %s", exc)
            return self._fallback_explicit_mention(normalized_text, reason=str(exc))

        threshold = self.settings.explicit_intent_confidence_threshold
        clarification_threshold = self.settings.explicit_intent_clarification_threshold

        if (
            result.intent == "CREATE_TASK"
            and result.confidence >= threshold
            and result.normalized_command
        ):
            return MessageTriageResult(
                intent=MessageIntent.EXPLICIT_NEW_TASK,
                normalized_text=result.normalized_command,
                reason=result.reason or "llm explicit create task",
                confidence=result.confidence,
                task_type=result.task_type,
                clarifying_questions=result.clarifying_questions,
                raw_intent=result.raw,
            )

        if result.requires_clarification or (
            result.intent == "CREATE_TASK"
            and result.confidence >= clarification_threshold
        ):
            questions = result.clarifying_questions or [
                "你希望我输出文档、PPT，还是只做讨论摘要？"
            ]

            return MessageTriageResult(
                intent=MessageIntent.NEED_CLARIFICATION,
                normalized_text=normalized_text,
                reason=result.reason or "llm requires clarification",
                confidence=result.confidence,
                task_type=result.task_type,
                clarifying_questions=questions,
                raw_intent=result.raw,
            )

        if result.intent in {"CHAT", "UNKNOWN"}:
            return MessageTriageResult(
                intent=MessageIntent.CHAT
                if result.intent == "CHAT"
                else MessageIntent.UNKNOWN,
                normalized_text=normalized_text,
                reason=result.reason or f"llm intent: {result.intent}",
                confidence=result.confidence,
                raw_intent=result.raw,
            )

        return MessageTriageResult(
            intent=MessageIntent.UNKNOWN,
            normalized_text=normalized_text,
            reason=f"unsupported llm intent: {result.intent}",
            confidence=result.confidence,
            raw_intent=result.raw,
        )

    def _fallback_explicit_mention(
        self,
        normalized_text: str,
        *,
        reason: str,
    ) -> MessageTriageResult:
        if self._looks_like_explicit_task_command(normalized_text):
            return MessageTriageResult(
                intent=MessageIntent.EXPLICIT_NEW_TASK,
                normalized_text=normalized_text,
                reason=f"fallback rule matched explicit task: {reason}",
            )

        return MessageTriageResult(
            intent=MessageIntent.NEED_CLARIFICATION,
            normalized_text=normalized_text,
            reason=f"fallback needs clarification: {reason}",
            clarifying_questions=[
                "你希望我创建一个任务吗？",
                "如果是，请说明希望输出文档、PPT、摘要还是其他材料。",
            ],
        )

    @staticmethod
    def _looks_like_explicit_task_command(text: str) -> bool:
        action_keywords = [
            "帮我",
            "请",
            "生成",
            "整理",
            "总结",
            "汇总",
            "写",
            "创建",
            "输出",
            "做一个",
            "做一份",
            "沉淀",
        ]
        deliverable_keywords = [
            "文档",
            "方案",
            "报告",
            "PPT",
            "ppt",
            "演示稿",
            "会议纪要",
            "汇报材料",
            "摘要",
            "总结",
        ]

        return any(keyword in text for keyword in action_keywords) and any(
            keyword in text for keyword in deliverable_keywords
        )

    def _run_explicit_intent_detector(
        self,
        normalized_text: str,
        *,
        context_messages: list[dict] | None = None,
    ):
        import asyncio
        import threading

        if self.explicit_intent_detector is None:
            from packages.agent.intent.explicit_intent_detector import (
                ExplicitIntentDetector,
            )

            self.explicit_intent_detector = ExplicitIntentDetector()

        coro = self.explicit_intent_detector.detect(
            normalized_text,
            context_messages=context_messages,
        )

        try:
            asyncio.get_running_loop()
        except RuntimeError:
            return asyncio.run(coro)

        result = None
        error = None

        def runner():
            nonlocal result, error
            try:
                result = asyncio.run(coro)
            except Exception as exc:
                error = exc

        thread = threading.Thread(target=runner)
        thread.start()
        thread.join()

        if error is not None:
            raise error

        return result
