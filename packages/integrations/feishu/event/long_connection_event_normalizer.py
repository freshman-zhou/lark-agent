import json
from typing import Any

import lark_oapi as lark

from packages.integrations.feishu.event.feishu_event_dto import FeishuMessageEventDTO
from packages.integrations.feishu.im.event_parser import FeishuEventParser


class LongConnectionEventNormalizer:
    """把飞书 SDK 长连接事件对象转为内部统一 DTO。"""

    def __init__(self):
        self.parser = FeishuEventParser()

    def normalize(self, data: Any) -> FeishuMessageEventDTO | None:
        payload = self._sdk_event_to_dict(data)

        event = self.parser.parse_message_event(payload)
        if event is None:
            return None

        return FeishuMessageEventDTO(
            event_id=event.event_id,
            event_type=event.event_type,
            message_id=event.message_id,
            chat_id=event.chat_id,
            sender_id=event.sender_id,
            message_type=event.message_type,
            content=event.content,
            raw_event=event.raw,
        )

    @staticmethod
    def _sdk_event_to_dict(data: Any) -> dict:
        marshalled = lark.JSON.marshal(data)

        if isinstance(marshalled, dict):
            return marshalled

        if isinstance(marshalled, str):
            return json.loads(marshalled)

        raise TypeError(f"Unsupported Feishu SDK event marshal type: {type(marshalled)!r}")