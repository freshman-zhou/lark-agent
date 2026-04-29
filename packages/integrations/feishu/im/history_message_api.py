from typing import Any

import httpx

from packages.integrations.feishu.auth.token_manager import FeishuTokenManager
from packages.integrations.feishu.im.message_content_parser import MessageContentParser
from packages.shared.config import get_settings
from packages.shared.exceptions import FeishuApiException, FeishuMessageException
from packages.shared.logger import get_logger

logger = get_logger(__name__)


class FeishuHistoryMessageApi:
    """飞书历史消息 API。

    用于根据 chat_id 拉取最近一段群聊消息。
    """

    def __init__(self):
        self.settings = get_settings()
        self.token_manager = FeishuTokenManager()
        self.parser = MessageContentParser()

    async def list_chat_messages(
        self,
        chat_id: str,
        page_size: int = 50,
    ) -> list[dict[str, Any]]:
        if not chat_id:
            raise FeishuMessageException("chat_id is required")

        token = await self.token_manager.get_tenant_access_token()

        url = f"{self.settings.feishu_base_url}/im/v1/messages"

        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json; charset=utf-8",
        }

        params = {
            "container_id_type": "chat",
            "container_id": chat_id,
            "page_size": min(max(page_size, 1), 50),
            "sort_type": "ByCreateTimeDesc",
        }

        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.get(url, headers=headers, params=params)

        try:
            data = response.json()
        except Exception as exc:
            raise FeishuApiException(
                message="Failed to parse Feishu history message response",
                detail={
                    "status_code": response.status_code,
                    "text": response.text,
                },
            ) from exc

        if response.status_code != 200 or data.get("code") != 0:
            logger.warning("List Feishu history messages failed: %s", data)
            raise FeishuMessageException(
                message="Failed to list Feishu history messages",
                detail=data,
            )

        items = data.get("data", {}).get("items", []) or []

        messages = []
        for item in items:
            parsed = self.parser.parse_history_item(item)
            if parsed:
                messages.append(parsed)

        # 飞书按倒序返回时，这里转成正序，方便 LLM 理解对话过程
        messages.sort(key=lambda x: x.get("create_time", ""))

        return messages