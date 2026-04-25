import json
import re
from dataclasses import dataclass


@dataclass
class FeishuMessageEvent:
    event_id: str | None
    event_type: str | None
    message_id: str
    chat_id: str
    sender_id: str
    message_type: str
    content: str
    raw: dict


class FeishuEventParser:
    """解析飞书事件订阅回调。

    当前重点适配接收消息 v2.0：im.message.receive_v1。
    """

    @staticmethod
    def is_url_verification(payload: dict) -> bool:
        return payload.get("type") == "url_verification"

    @staticmethod
    def parse_message_event(payload: dict) -> FeishuMessageEvent | None:
        header = payload.get("header", {})
        event = payload.get("event", {})
        event_type = header.get("event_type") or payload.get("event_type")

        if event_type != "im.message.receive_v1":
            return None

        message = event.get("message", {})
        sender = event.get("sender", {})
        sender_id = (
            sender.get("sender_id", {}).get("open_id")
            or sender.get("sender_id", {}).get("user_id")
            or sender.get("sender_id", {}).get("union_id")
            or ""
        )

        raw_content = message.get("content", "")
        text = FeishuEventParser._extract_text(raw_content)
        text = FeishuEventParser._remove_bot_mention_text(text, message.get("mentions", []))

        return FeishuMessageEvent(
            event_id=header.get("event_id"),
            event_type=event_type,
            message_id=message.get("message_id", ""),
            chat_id=message.get("chat_id", ""),
            sender_id=sender_id,
            message_type=message.get("message_type", ""),
            content=text.strip(),
            raw=payload,
        )

    @staticmethod
    def _extract_text(raw_content: str | dict) -> str:
        if isinstance(raw_content, dict):
            content_obj = raw_content
        else:
            try:
                content_obj = json.loads(raw_content) if raw_content else {}
            except json.JSONDecodeError:
                return raw_content

        # text 类型常见格式：{"text":"xxx"}
        if "text" in content_obj:
            return str(content_obj.get("text", ""))

        # post 富文本可能是多层结构，这里做第一版粗略提取。
        if "content" in content_obj and isinstance(content_obj["content"], list):
            parts: list[str] = []
            for line in content_obj["content"]:
                if isinstance(line, list):
                    for item in line:
                        if isinstance(item, dict) and item.get("tag") == "text":
                            parts.append(item.get("text", ""))
            return "".join(parts)

        return str(content_obj)

    @staticmethod
    def _remove_bot_mention_text(text: str, mentions: list[dict]) -> str:
        cleaned = text
        for mention in mentions or []:
            key = mention.get("key")
            name = mention.get("name")
            if key:
                cleaned = cleaned.replace(key, "")
            if name:
                cleaned = cleaned.replace(f"@{name}", "")
        # 清理类似 @_user_1 这种占位。
        cleaned = re.sub(r"@_user_\d+", "", cleaned)
        return cleaned.strip()