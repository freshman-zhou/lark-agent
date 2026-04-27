import json
from typing import Any

import httpx

from packages.integrations.feishu.auth.token_manager import FeishuTokenManager
from packages.shared.config import get_settings
from packages.integrations.feishu.client import FeishuClient
from packages.integrations.feishu.auth.token_manager import FeishuTokenManager
from packages.shared.exceptions import FeishuApiException, FeishuMessageException
from packages.shared.logger import get_logger

logger = get_logger(__name__)

class FeishuMessageApi:
    def __init__(self):
        self.client = FeishuClient()
        self.token_manager = FeishuTokenManager()
        self.settings = get_settings()

    async def reply_text(self, message_id: str, text: str) -> dict:
        if not message_id:
            raise FeishuMessageException("message_id is required")

        return await self._reply_message(
            message_id=message_id,
            msg_type="text",
            content={
                "text": text,
            },
        )

    async def reply_card(self, message_id: str, card: dict[str, Any]) -> dict:
        """回复一张交互卡片。"""

        if not message_id:
            raise FeishuMessageException("message_id is required")

        return await self._reply_message(
            message_id=message_id,
            msg_type="interactive",
            content=card,
        )

    async def send_text_to_chat(self, chat_id: str, text: str) -> dict:
        if not chat_id:
            raise FeishuMessageException("chat_id is required")

        return await self._send_message(
            receive_id_type="chat_id",
            receive_id=chat_id,
            msg_type="text",
            content={
                "text": text,
            },
        )

    async def send_card_to_chat(self, chat_id: str, card: dict[str, Any]) -> dict:
        if not chat_id:
            raise FeishuMessageException("chat_id is required")

        return await self._send_message(
            receive_id_type="chat_id",
            receive_id=chat_id,
            msg_type="interactive",
            content=card,
        )

    async def _reply_message(
        self,
        message_id: str,
        msg_type: str,
        content: dict[str, Any],
    ) -> dict:
        token = await self.token_manager.get_tenant_access_token()

        url = f"{self.settings.feishu_base_url}/im/v1/messages/{message_id}/reply"

        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json; charset=utf-8",
        }

        body = {
            "msg_type": msg_type,
            "content": json.dumps(content, ensure_ascii=False),
        }

        async with httpx.AsyncClient(timeout=15) as client:
            response = await client.post(url, headers=headers, json=body)

        return self._parse_feishu_response(
            response=response,
            action=f"reply_message:{msg_type}",
        )

    async def _send_message(
        self,
        receive_id_type: str,
        receive_id: str,
        msg_type: str,
        content: dict[str, Any],
    ) -> dict:
        token = await self.token_manager.get_tenant_access_token()

        url = (
            f"{self.settings.feishu_base_url}/im/v1/messages"
            f"?receive_id_type={receive_id_type}"
        )

        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json; charset=utf-8",
        }

        body = {
            "receive_id": receive_id,
            "msg_type": msg_type,
            "content": json.dumps(content, ensure_ascii=False),
        }

        async with httpx.AsyncClient(timeout=15) as client:
            response = await client.post(url, headers=headers, json=body)

        return self._parse_feishu_response(
            response=response,
            action=f"send_message:{msg_type}",
        )

    @staticmethod
    def _parse_feishu_response(response: httpx.Response, action: str) -> dict:
        try:
            data = response.json()
        except Exception as exc:
            raise FeishuApiException(
                message=f"Failed to parse Feishu response: {action}",
                detail={
                    "status_code": response.status_code,
                    "text": response.text,
                },
            ) from exc

        if response.status_code != 200 or data.get("code") != 0:
            logger.warning("Feishu API failed: action=%s data=%s", action, data)
            raise FeishuMessageException(
                message=f"Feishu message API failed: {action}",
                detail=data,
            )

        logger.info("Feishu API success: action=%s", action)
        return data