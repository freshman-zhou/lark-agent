# packages/application/message_triage_service.py

import json
import re
from dataclasses import dataclass
from enum import Enum

from packages.integrations.feishu.event.feishu_event_dto import FeishuMessageEventDTO


class MessageIntent(str, Enum):
    EMPTY = "EMPTY"
    IGNORE = "IGNORE"
    NEW_TASK_REQUEST = "NEW_TASK_REQUEST"
    CONFIRM_TASK = "CONFIRM_TASK"
    CANCEL_TASK = "CANCEL_TASK"
    CLARIFY_REPLY = "CLARIFY_REPLY"
    UNKNOWN = "UNKNOWN"


@dataclass
class MessageTriageResult:
    intent: MessageIntent
    normalized_text: str
    task_id: str | None = None
    reason: str | None = None


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

    def triage_feishu_message(
        self,
        event: FeishuMessageEventDTO,
    ) -> MessageTriageResult:
        text = self.normalize_message_content(event.content)

        return self.triage_text(text)

    def triage_text(self, text: str) -> MessageTriageResult:
        normalized_text = self.normalize_message_content(text)

        if not normalized_text:
            return MessageTriageResult(
                intent=MessageIntent.EMPTY,
                normalized_text="",
                reason="empty message",
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

        if self._looks_like_new_task(normalized_text):
            return MessageTriageResult(
                intent=MessageIntent.NEW_TASK_REQUEST,
                normalized_text=normalized_text,
                reason="looks like new task request",
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