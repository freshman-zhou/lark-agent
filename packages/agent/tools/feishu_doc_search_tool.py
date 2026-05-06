from typing import Any

from packages.agent.tools.base_tool import BaseTool, ToolResult
from packages.integrations.feishu.doc.cli_runner import FeishuDocCliRunner
from packages.integrations.feishu.doc.document_cli_api import FeishuDocumentCliApi
from packages.shared.config import get_settings


class FeishuDocSearchTool(BaseTool):
    name = "feishu_doc_search"
    description = "通过 lark-cli 搜索飞书内部文档、知识库和表格。"

    def __init__(self):
        self.settings = get_settings()
        self.runner = FeishuDocCliRunner()

    async def run(self, **kwargs) -> ToolResult:
        query = str(kwargs.get("query") or "").strip()
        limit = int(kwargs.get("limit") or self.settings.research_max_results_per_query)

        if not self.settings.research_feishu_doc_search_enabled:
            return ToolResult(success=True, data={"items": [], "skipped": "feishu doc search disabled"})

        if not query:
            return ToolResult(success=False, error="query is required")

        try:
            result = await self.runner.run_template(
                self.settings.research_feishu_doc_search_command_template,
                {
                    "query": query,
                    "limit": str(limit),
                },
            )
            payload = FeishuDocumentCliApi._parse_json_or_text(result.stdout)
        except Exception as exc:
            return ToolResult(success=False, error=str(exc))

        return ToolResult(
            success=True,
            data={
                "query": query,
                "items": self._normalize_items(payload)[:limit],
                "raw": payload,
            },
        )

    def _normalize_items(self, payload: Any) -> list[dict[str, Any]]:
        candidates = self._find_result_list(payload)
        normalized = []

        for item in candidates:
            if not isinstance(item, dict):
                continue

            title = (
                item.get("title")
                or item.get("name")
                or item.get("file_name")
                or item.get("docs_title")
                or ""
            )
            url = item.get("url") or item.get("link") or item.get("docs_url") or item.get("web_url") or ""
            snippet = (
                item.get("snippet")
                or item.get("summary")
                or item.get("description")
                or item.get("content")
                or ""
            )

            if title or url or snippet:
                normalized.append(
                    {
                        "source_type": "feishu_doc",
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

        for key in ["results", "items", "data"]:
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
