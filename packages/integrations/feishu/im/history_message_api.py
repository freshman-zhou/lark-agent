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

        if self.settings.feishu_history_mock:
            return self._mock_chat_messages(chat_id)

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

    @staticmethod
    def _mock_chat_messages(chat_id: str) -> list[dict[str, Any]]:
        return [
            {
                "message_id": "mock_msg_001",
                "sender_id": "ou_product",
                "sender_type": "user",
                "message_type": "text",
                "content": "我们需要把 Agent-Pilot 做成从 IM 讨论到文档和 PPT 的闭环，重点展示 AI Agent 是主驾驶。",
                "create_time": "2026-05-07 10:00:00",
                "raw": {"mock": True, "chat_id": chat_id},
            },
            {
                "message_id": "mock_msg_002",
                "sender_id": "ou_design",
                "sender_type": "user",
                "message_type": "text",
                "content": "GUI 工作台不应该抢任务入口，飞书卡片负责确认，工作台负责展示进度和多人编辑生成的大纲。",
                "create_time": "2026-05-07 10:02:00",
                "raw": {"mock": True, "chat_id": chat_id},
            },
            {
                "message_id": "mock_msg_003",
                "sender_id": "ou_engineer",
                "sender_type": "user",
                "message_type": "text",
                "content": "多端协同先做结构化 artifact，包括文档大纲、文档草稿、PPT 大纲和 slide deck，定稿后继续 LangGraph。",
                "create_time": "2026-05-07 10:05:00",
                "raw": {"mock": True, "chat_id": chat_id},
            },
            {
                "message_id": "mock_msg_004",
                "sender_id": "ou_pm",
                "sender_type": "user",
                "message_type": "text",
                "content": "演示链路要体现三次人工确认：文档大纲、PPT 大纲、完整 PPT。用户可以修改后定稿或要求重新生成。",
                "create_time": "2026-05-07 10:08:00",
                "raw": {"mock": True, "chat_id": chat_id},
            },
            {
                "message_id": "mock_msg_005",
                "sender_id": "ou_product",
                "sender_type": "user",
                "message_type": "text",
                "content": "最终产出需要包含飞书文档链接、演示稿链接和任务执行摘要，方便回到群里汇报和归档。",
                "create_time": "2026-05-07 10:12:00",
                "raw": {"mock": True, "chat_id": chat_id},
            },
        ]
