from packages.integrations.feishu.event.feishu_event_dto import FeishuMessageEventDTO
from packages.integrations.feishu.im.event_parser import FeishuEventParser


class WebhookEventNormalizer:
    """把飞书 HTTP Webhook 原始 payload 转为内部统一 DTO。"""

    def __init__(self):
        self.parser = FeishuEventParser()

    def normalize(self, payload: dict) -> FeishuMessageEventDTO | None:
        event = self.parser.parse_message_event(payload)
        if event is None:
            return None

        return FeishuMessageEventDTO(
            event_id=event.event_id,
            event_type=event.event_type,
            message_id=event.message_id,
            chat_id=event.chat_id,
            chat_type=event.chat_type,
            sender_id=event.sender_id,
            message_type=event.message_type,
            content=event.content,
            mentions=event.mentions,
            is_mention_bot=event.is_mention_bot,
            raw_event=event.raw,
        )
