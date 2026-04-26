import json

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
        self.tokenManager = FeishuTokenManager()
        self.settings = get_settings()

    async def send_text_to_chat(self, chat_id: str, text: str) -> dict:
        if not chat_id:
            raise FeishuMessageException("chat_id is required")
        if not text:
            raise FeishuMessageException("text cannot be empty")

        # 2. 获取 tenant token
        token = await self.tokenManager.get_tenant_access_token()
        url = f"{self.settings.feishu_base_url}/im/v1/messages"

        # 3. 请求头（标准格式）
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json; charset=utf-8",
        }

        # 4. 请求体（飞书标准格式）
        body = {
            "receive_id": chat_id,
            "msg_type": "text",
            "content": json.dumps({"text": text}, ensure_ascii=False),
        }

        # 5. 独立异步客户端 + 超时保护
        async with httpx.AsyncClient(timeout=15) as client:
            response = await client.post(
                url,
                headers=headers,
                json=body,
                params={"receive_id_type": "chat_id"}
            )

        # 6. 解析响应异常处理
        try:
            data = response.json()
        except Exception as exc:
            raise FeishuApiException(
                message="Failed to parse Feishu send message response",
                detail={
                    "status_code": response.status_code,
                    "text": response.text,
                },
            ) from exc

        # 7. 飞书接口错误判断（code != 0 代表失败）
        if response.status_code != 200 or data.get("code") != 0:
            logger.warning("Send Feishu message to chat failed: %s", data)
            raise FeishuMessageException(
                message="Failed to send Feishu message to chat",
                detail=data,
            )

        logger.info("Send Feishu message to chat success, chat_id=%s", chat_id)
        return data

    async def reply_text(self, message_id: str, text: str) -> dict:
        """回复指定飞书消息。"""

        if not message_id:
            raise FeishuMessageException("message_id is required")

        token = await self.tokenManager.get_tenant_access_token()

        url = f"{self.settings.feishu_base_url}/im/v1/messages/{message_id}/reply"

        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json; charset=utf-8",
        }

        body = {
            "msg_type": "text",
            "content": json.dumps(
                {
                    "text": text,
                },
                ensure_ascii=False,
            ),
        }

        async with httpx.AsyncClient(timeout=15) as client:
            response = await client.post(url, headers=headers, json=body)

        try:
            data = response.json()
        except Exception as exc:
            raise FeishuApiException(
                message="Failed to parse Feishu reply response",
                detail={
                    "status_code": response.status_code,
                    "text": response.text,
                },
            ) from exc

        if response.status_code != 200 or data.get("code") != 0:
            logger.warning("Reply Feishu message failed: %s", data)
            raise FeishuMessageException(
                message="Failed to reply Feishu message",
                detail=data,
            )

        logger.info("Reply Feishu message success, message_id=%s", message_id)

        return data