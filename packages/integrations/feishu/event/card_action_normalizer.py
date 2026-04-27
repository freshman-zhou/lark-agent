import json
from dataclasses import dataclass
from typing import Any

import lark_oapi as lark


@dataclass
class FeishuCardActionDTO:
    action: str
    task_id: str | None
    operator_id: str | None
    open_message_id: str | None
    open_chat_id: str | None
    raw_event: dict[str, Any]


class CardActionNormalizer:
    """把飞书 card.action.trigger 回调转为内部 DTO。

    飞书 SDK marshal 后的结构在不同 SDK 版本中可能略有差异，
    所以这里做多路径兼容。
    """

    def normalize(self, data: Any) -> FeishuCardActionDTO:
        payload = self._sdk_event_to_dict(data)

        event = payload.get("event", payload)

        action_obj = event.get("action", {}) or {}
        value = action_obj.get("value") or {}

        if isinstance(value, str):
            try:
                value = json.loads(value)
            except Exception:
                value = {}

        operator = event.get("operator", {}) or {}
        context = event.get("context", {}) or {}

        operator_id = (
            self._deep_get(operator, ["open_id"])
            or self._deep_get(operator, ["user_id", "open_id"])
            or self._deep_get(operator, ["user_id", "user_id"])
            or self._deep_get(operator, ["user_id", "union_id"])
        )

        open_message_id = (
            context.get("open_message_id")
            or event.get("open_message_id")
            or payload.get("open_message_id")
        )

        open_chat_id = (
            context.get("open_chat_id")
            or event.get("open_chat_id")
            or payload.get("open_chat_id")
        )

        return FeishuCardActionDTO(
            action=value.get("action", ""),
            task_id=value.get("task_id"),
            operator_id=operator_id,
            open_message_id=open_message_id,
            open_chat_id=open_chat_id,
            raw_event=payload,
        )

    @staticmethod
    def _sdk_event_to_dict(data: Any) -> dict:
        marshalled = lark.JSON.marshal(data)

        if isinstance(marshalled, dict):
            return marshalled

        if isinstance(marshalled, str):
            return json.loads(marshalled)

        raise TypeError(f"Unsupported Feishu SDK event marshal type: {type(marshalled)!r}")

    @staticmethod
    def _deep_get(data: dict, keys: list[str]) -> Any:
        current = data
        for key in keys:
            if not isinstance(current, dict):
                return None
            current = current.get(key)
        return current