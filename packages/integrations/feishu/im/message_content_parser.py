import json
from typing import Any


class MessageContentParser:
    """解析飞书消息内容。

    第一版重点支持 text 和 post。
    图片、文件、表格等富媒体后续再扩展。
    """

    def parse_history_item(self, item: dict[str, Any]) -> dict[str, Any] | None:
        message_id = item.get("message_id")
        msg_type = item.get("msg_type") or item.get("message_type")
        create_time = item.get("create_time") or item.get("update_time")

        sender = item.get("sender", {}) or {}
        sender_id = (
            sender.get("id")
            or sender.get("sender_id")
            or sender.get("open_id")
            or sender.get("user_id")
        )
        sender_type = sender.get("sender_type") or sender.get("type")

        body = item.get("body", {}) or {}
        raw_content = body.get("content") or item.get("content") or ""

        content = self.parse_content(
            msg_type=msg_type,
            raw_content=raw_content,
        )

        if not content:
            return None

        return {
            "message_id": message_id,
            "sender_id": sender_id,
            "sender_type": sender_type,
            "message_type": msg_type,
            "content": content,
            "create_time": create_time,
            "raw": item,
        }

    def parse_content(self, msg_type: str | None, raw_content: str | dict) -> str:
        if raw_content is None:
            return ""

        if isinstance(raw_content, dict):
            content_obj = raw_content
        else:
            try:
                content_obj = json.loads(raw_content)
            except Exception:
                return str(raw_content).strip()

        if msg_type == "text":
            return self._parse_text(content_obj)

        if msg_type == "post":
            return self._parse_post(content_obj)

        # 其他类型先尽量提取 text/content
        return (
            content_obj.get("text")
            or content_obj.get("content")
            or content_obj.get("title")
            or ""
        ).strip()

    @staticmethod
    def _parse_text(content_obj: dict) -> str:
        return (
            content_obj.get("text")
            or content_obj.get("content")
            or ""
        ).strip()

    @staticmethod
    def _parse_post(content_obj: dict) -> str:
        """解析飞书 post 富文本。

        常见结构：
        {
          "title": "...",
          "content": [
            [
              {"tag": "text", "text": "..."},
              {"tag": "a", "text": "...", "href": "..."}
            ]
          ]
        }
        """
        title = content_obj.get("title") or ""
        blocks = content_obj.get("content") or []

        parts = []

        if title:
            parts.append(title)

        for line in blocks:
            if not isinstance(line, list):
                continue

            line_parts = []
            for node in line:
                if not isinstance(node, dict):
                    continue

                tag = node.get("tag")

                if tag == "text":
                    line_parts.append(node.get("text", ""))

                elif tag == "a":
                    text = node.get("text") or node.get("href") or ""
                    line_parts.append(text)

                elif tag == "at":
                    name = node.get("user_name") or node.get("name") or ""
                    if name:
                        line_parts.append(f"@{name}")

                elif tag == "img":
                    line_parts.append("[图片]")

                else:
                    text = node.get("text") or node.get("content") or ""
                    if text:
                        line_parts.append(text)

            line_text = "".join(line_parts).strip()
            if line_text:
                parts.append(line_text)

        return "\n".join(parts).strip()