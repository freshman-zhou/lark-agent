from typing import Any

import httpx

from packages.agent.tools.base_tool import BaseTool, ToolResult
from packages.agent.tools.web_search_http_tool import WebSearchHttpTool
from packages.shared.config import get_settings


class ImageSearchHttpTool(BaseTool):
    name = "image_search"
    description = "通过可配置 HTTP API 检索 PPT 候选图片素材。"

    def __init__(self):
        self.settings = get_settings()

    async def run(self, **kwargs) -> ToolResult:
        query = str(kwargs.get("query") or "").strip()
        limit = int(kwargs.get("limit") or self.settings.image_search_max_results_per_query)

        if not self.settings.image_search_enabled:
            return ToolResult(success=True, data={"items": [], "skipped": "image search disabled"})

        if not self.settings.image_search_api_url:
            return ToolResult(success=True, data={"items": [], "skipped": "image search api url missing"})

        if not query:
            return ToolResult(success=False, error="query is required")

        provider = self.settings.image_search_provider.lower()
        try:
            async with httpx.AsyncClient(timeout=self.settings.image_search_timeout) as client:
                response = await self._request(client, provider=provider, query=query, limit=limit)
            response.raise_for_status()
            payload = WebSearchHttpTool._parse_response_payload(response)
        except Exception as exc:
            return ToolResult(success=False, error=str(exc))

        return ToolResult(
            success=True,
            data={
                "query": query,
                "provider": provider,
                "items": self._normalize_items(payload)[:limit],
                "raw": payload,
            },
        )

    async def _request(
        self,
        client: httpx.AsyncClient,
        *,
        provider: str,
        query: str,
        limit: int,
    ) -> httpx.Response:
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
        }
        if self.settings.image_search_api_key:
            headers["Authorization"] = f"Bearer {self.settings.image_search_api_key}"

        if provider == "volcengine":
            payload = {
                "Query": query,
                "SearchType": "image",
                "Count": limit,
                "Filter": {
                    "NeedContent": False,
                    "NeedUrl": True,
                },
                "NeedSummary": False,
            }
            return await client.post(self.settings.image_search_api_url, headers=headers, json=payload)

        return await client.get(
            self.settings.image_search_api_url,
            headers=headers,
            params={"q": query, "limit": limit, "type": "image"},
        )

    def _normalize_items(self, payload: Any) -> list[dict[str, Any]]:
        candidates = WebSearchHttpTool()._find_result_list(payload)
        items = []

        for item in candidates:
            if not isinstance(item, dict):
                continue

            title = item.get("title") or item.get("Title") or item.get("name") or "候选图片"
            image_url = (
                item.get("image_url")
                or item.get("ImageUrl")
                or item.get("thumbnail")
                or item.get("Thumbnail")
                or item.get("url")
                or item.get("Url")
            )
            source_url = item.get("source_url") or item.get("SourceUrl") or item.get("link") or item.get("Link") or ""

            if image_url:
                items.append(
                    {
                        "source_type": "image",
                        "title": str(title),
                        "image_url": str(image_url),
                        "source_url": str(source_url),
                        "license": "unknown",
                    }
                )

        return items
