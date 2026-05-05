import json
import re

import httpx

from packages.agent.llm.llm_client import LLMClient
from packages.shared.config import get_settings
from packages.shared.exceptions import AgentException


class OpenAILLMClient(LLMClient):
    """兼容常见 /v1/chat/completions 格式的 LLM 客户端。"""

    def __init__(self):
        self.settings = get_settings()

    async def chat_json(
        self,
        system_prompt: str,
        user_prompt: str,
    ) -> dict:
        content = await self.chat_text(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
        )

        return self._parse_json_content(content)

    async def chat_text(
        self,
        system_prompt: str,
        user_prompt: str,
    ) -> str:
        if not self.settings.llm_base_url:
            raise AgentException("LLM_BASE_URL is empty")

        if not self.settings.llm_api_key:
            raise AgentException("LLM_API_KEY is empty")

        if not self.settings.llm_model:
            raise AgentException("LLM_MODEL is empty")

        url = self._build_chat_completions_url(self.settings.llm_base_url)

        headers = {
            "Authorization": f"Bearer {self.settings.llm_api_key}",
            "Content-Type": "application/json",
        }

        payload = {
            "model": self.settings.llm_model,
            "temperature": 0.2,
            "messages": [
                {
                    "role": "system",
                    "content": system_prompt,
                },
                {
                    "role": "user",
                    "content": user_prompt,
                },
            ],
        }

        async with httpx.AsyncClient(timeout=self.settings.llm_timeout) as client:
            response = await client.post(url, headers=headers, json=payload)

        if response.status_code >= 400:
            try:
                detail = response.json()
            except Exception:
                detail = {
                    "status_code": response.status_code,
                    "text": response.text,
                    "url": url,
                }
            raise AgentException(
                message=f"LLM request failed: HTTP {response.status_code}",
                detail=detail,
            )

        try:
            data = response.json()
        except Exception as exc:
            raise AgentException(
                message="Failed to parse LLM response",
                detail={
                    "status_code": response.status_code,
                    "text": response.text,
                },
            ) from exc

        content = (
            data.get("choices", [{}])[0]
            .get("message", {})
            .get("content", "")
        )

        if not content:
            raise AgentException(
                message="LLM response content is empty",
                detail=data,
            )

        return str(content).strip()

    @staticmethod
    def _parse_json_content(content: str) -> dict:
        content = content.strip()

        try:
            return json.loads(content)
        except Exception:
            pass

        # 兼容 ```json ... ``` 包裹
        match = re.search(r"```json\s*(.*?)```", content, re.DOTALL)
        if match:
            return json.loads(match.group(1).strip())

        match = re.search(r"```\s*(.*?)```", content, re.DOTALL)
        if match:
            return json.loads(match.group(1).strip())

        # 兼容前后有解释文字，尽量抓取第一个 JSON 对象
        start = content.find("{")
        end = content.rfind("}")
        if start != -1 and end != -1 and end > start:
            return json.loads(content[start : end + 1])

        raise AgentException(
            message="LLM did not return valid JSON",
            detail={
                "content": content,
            },
        )

    @staticmethod
    def _build_chat_completions_url(base_url: str) -> str:
        url = base_url.rstrip("/")
        if url.endswith("/chat/completions"):
            return url
        return f"{url}/chat/completions"
