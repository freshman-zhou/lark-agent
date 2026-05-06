from typing import Any

import httpx

from packages.agent.tools.base_tool import BaseTool, ToolResult
from packages.shared.config import get_settings


class WebSearchHttpTool(BaseTool):
    name = "web_search"
    description = "通过可配置 HTTP API 搜索互联网资料。"

    def __init__(self):
        self.settings = get_settings()

    async def run(self, **kwargs) -> ToolResult:
        query = str(kwargs.get("query") or "").strip()
        limit = int(kwargs.get("limit") or self.settings.research_max_results_per_query)

        if not self.settings.research_web_enabled:
            return ToolResult(success=True, data={"items": [], "skipped": "web search disabled"})

        if not self.settings.research_web_api_url:
            return ToolResult(success=True, data={"items": [], "skipped": "web search api url missing"})

        if not query:
            return ToolResult(success=False, error="query is required")

        provider = self.settings.research_web_api_provider.lower()

        try:
            async with httpx.AsyncClient(timeout=self.settings.research_web_timeout) as client:
                response = await self._request(client, provider=provider, query=query, limit=limit)
            response.raise_for_status()
            payload = self._parse_response_payload(response)
        except Exception as exc:
            return ToolResult(success=False, error=str(exc))

        return ToolResult(
            success=True,
            data={
                "query": query,
                "provider": provider,
                "items": self._normalize_items(payload, provider=provider)[:limit],
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
        url = self.settings.research_web_api_url
        api_key = self.settings.research_web_api_key

        if provider == "tavily":
            headers = {"Content-Type": "application/json"}
            payload: dict[str, Any] = {
                "query": query,
                "max_results": limit,
                "search_depth": "basic",
            }
            if api_key:
                payload["api_key"] = api_key
            return await client.post(url, headers=headers, json=payload)

        if provider == "brave":
            headers = {"Accept": "application/json"}
            if api_key:
                headers["X-Subscription-Token"] = api_key
            return await client.get(url, headers=headers, params={"q": query, "count": limit})

        if provider == "volcengine":
            headers = {
                "Accept": "application/json",
                "Content-Type": "application/json",
            }
            if api_key:
                headers["Authorization"] = f"Bearer {api_key}"
            payload = {
                "Query": query,
                "SearchType": "web_summary",
                "Count": limit,
                "Filter": {
                    "NeedContent": False,
                    "NeedUrl": True,
                },
                "NeedSummary": True,
            }
            return await client.post(url, headers=headers, json=payload)

        headers = {"Accept": "application/json"}
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"
        return await client.get(url, headers=headers, params={"q": query, "limit": limit})

    @staticmethod
    def _parse_response_payload(response: httpx.Response):
        text = response.text.strip()
        if not text:
            return {}

        try:
            return response.json()
        except Exception:
            pass

        lines = [line.strip() for line in text.splitlines() if line.strip()]
        parsed_lines = []
        for line in lines:
            try:
                parsed_lines.append(httpx.Response(200, text=line).json())
            except Exception:
                parsed_lines.append({"text": line})

        return {"results": parsed_lines, "raw_text": text}

    def _normalize_items(self, payload: Any, *, provider: str) -> list[dict[str, Any]]:
        if provider == "tavily":
            results = payload.get("results") if isinstance(payload, dict) else []
        elif provider == "brave":
            web = payload.get("web", {}) if isinstance(payload, dict) else {}
            results = web.get("results") or []
        elif provider == "volcengine":
            results = self._find_result_list(payload)
        elif isinstance(payload, dict):
            results = payload.get("results") or payload.get("items") or payload.get("data") or []
        else:
            results = []

        normalized = []
        for item in results:
            if not isinstance(item, dict):
                continue

            if "text" in item and len(item) == 1:
                normalized.append(
                    {
                        "source_type": "web",
                        "title": "火山联网搜索结果",
                        "url": "",
                        "snippet": str(item.get("text") or ""),
                    }
                )
                continue

            title = item.get("title") or item.get("Title") or item.get("name") or ""
            url = item.get("url") or item.get("link") or item.get("site_url") or item.get("SourceUrl") or ""
            snippet = (
                item.get("content")
                or item.get("snippet")
                or item.get("summary")
                or item.get("description")
                or item.get("abstract")
                or item.get("text")
                or item.get("Summary")
                or item.get("Content")
                or ""
            )

            if title or url or snippet:
                normalized.append(
                    {
                        "source_type": "web",
                        "title": str(title),
                        "url": str(url),
                        "snippet": str(snippet),
                    }
                )

        return normalized

    def _find_result_list(self, payload: Any) -> list:
        if isinstance(payload, list):
            return payload

        if not isinstance(payload, dict):
            return []

        for key in [
            "results",
            "items",
            "data",
            "docs",
            "web_pages",
            "references",
            "SearchResult",
            "SearchResults",
            "Pages",
            "Result",
        ]:
            value = payload.get(key)
            if isinstance(value, list):
                return value
            if isinstance(value, dict):
                found = self._find_result_list(value)
                if found:
                    return found

        for value in payload.values():
            found = self._find_result_list(value)
            if found:
                return found

        return []
