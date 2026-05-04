from dataclasses import dataclass
from typing import Any


@dataclass(slots=True)
class FeishuMessageEventDTO:
    """系统内部统一消息事件模型。
    不管事件来自 HTTP Webhook 还是 SDK 长连接，进入 application 层前都先转成这个 DTO。
    这样 FeishuEventService 不需要关心飞书原始 payload 结构。
    """

    event_id: str | None
    event_type: str | None
    message_id: str
    chat_id: str
    chat_type: str | None
    sender_id: str
    message_type: str
    content: str
    mentions: list[dict[str, Any]]
    is_mention_bot: bool
    raw_event: dict[str, Any]

    def is_valid_text_command(self) -> bool:
        return bool(self.message_id and self.chat_id and self.sender_id and self.content.strip())
