from packages.agent.skills.base_skill import BaseSkill, SkillResult
from packages.agent.tools.tool_registry import ToolRegistry
from packages.shared.config import get_settings


class ResearchCollectSkill(BaseSkill):
    name = "research.collect"
    description = "按 research_plan 执行互联网和飞书内部文档检索，生成资料上下文。"

    def __init__(self):
        self.settings = get_settings()
        self.tool_registry = ToolRegistry()

    async def run(self, params: dict, context) -> SkillResult:
        plan = context.memory.get("research_plan") or {}

        if not plan.get("needs_research"):
            research_context = {
                "items": [],
                "summary": "本次文档生成未触发外部资料检索。",
                "queries": [],
            }
            context.memory["research_context"] = research_context
            return SkillResult(
                success=True,
                message="无需补充资料，已跳过检索",
                data={"research_context": research_context},
            )

        all_items = []
        query_results = []

        for query in plan.get("queries", [])[: self.settings.research_max_queries]:
            query_text = query.get("query")
            source = query.get("source") or "both"
            section_id = query.get("section_id") or ""

            tools = []
            if source in {"web", "both"}:
                tools.append("web_search")
            if source in {"feishu_doc", "both"}:
                tools.append("feishu_doc_search")

            for tool_name in tools:
                result = await self.tool_registry.run(
                    tool_name,
                    query=query_text,
                    limit=self.settings.research_max_results_per_query,
                )
                data = result.data or {}
                items = data.get("items") or []
                enriched_items = [
                    {
                        **item,
                        "query": query_text,
                        "section_id": section_id,
                        "purpose": query.get("purpose") or "",
                    }
                    for item in items
                ]
                all_items.extend(enriched_items)
                query_results.append(
                    {
                        "tool": tool_name,
                        "query": query_text,
                        "success": result.success,
                        "error": result.error,
                        "item_count": len(items),
                        "skipped": data.get("skipped"),
                    }
                )

        research_context = {
            "items": self._dedupe_items(all_items),
            "queries": query_results,
            "summary": self._build_summary(all_items),
        }
        context.memory["research_context"] = research_context

        return SkillResult(
            success=True,
            message="已完成补充资料检索",
            data={"research_context": research_context},
        )

    @staticmethod
    def _dedupe_items(items: list[dict]) -> list[dict]:
        seen = set()
        deduped = []
        for item in items:
            key = item.get("url") or f"{item.get('source_type')}:{item.get('title')}:{item.get('snippet')}"
            if key in seen:
                continue
            seen.add(key)
            deduped.append(item)
        return deduped

    @staticmethod
    def _build_summary(items: list[dict]) -> str:
        if not items:
            return "未检索到可用补充资料。"

        lines = []
        for item in items[:8]:
            title = item.get("title") or "未命名资料"
            source_type = item.get("source_type") or "unknown"
            snippet = item.get("snippet") or ""
            lines.append(f"- [{source_type}] {title}: {snippet}")
        return "\n".join(lines)
