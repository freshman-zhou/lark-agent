from packages.agent.skills.base_skill import BaseSkill, SkillResult
from packages.agent.tools.tool_registry import ToolRegistry
from packages.shared.config import get_settings


class SlideResearchCollectSkill(BaseSkill):
    name = "research.collect_for_slide"
    description = "按 slide_research_plan 为 PPT 收集互联网和飞书内部资料。"

    def __init__(self):
        self.settings = get_settings()
        self.tool_registry = ToolRegistry()

    async def run(self, params: dict, context) -> SkillResult:
        plan = context.memory.get("slide_research_plan") or {}
        if not plan.get("needs_research"):
            research_context = {"items": [], "summary": "本次 PPT 未触发资料检索。", "queries": []}
            context.memory["slide_research_context"] = research_context
            return SkillResult(success=True, message="无需补充 PPT 资料，已跳过", data={"slide_research_context": research_context})

        all_items = []
        query_results = []
        for query in plan.get("queries", [])[: self.settings.research_max_queries]:
            tools = []
            source = query.get("source") or "both"
            if source in {"web", "both"}:
                tools.append("web_search")
            if source in {"feishu_doc", "both"}:
                tools.append("feishu_doc_search")

            for tool_name in tools:
                result = await self.tool_registry.run(tool_name, query=query.get("query"), limit=self.settings.research_max_results_per_query)
                data = result.data or {}
                items = data.get("items") or []
                all_items.extend([{**item, "slide_id": query.get("slide_id") or "", "query": query.get("query"), "purpose": query.get("purpose") or ""} for item in items])
                query_results.append({"tool": tool_name, "query": query.get("query"), "success": result.success, "error": result.error, "item_count": len(items), "skipped": data.get("skipped")})

        deduped = self._dedupe(all_items)
        research_context = {"items": deduped, "queries": query_results, "summary": self._summary(deduped)}
        context.memory["slide_research_context"] = research_context

        return SkillResult(success=True, message="已完成 PPT 补充资料检索", data={"slide_research_context": research_context})

    @staticmethod
    def _dedupe(items: list[dict]) -> list[dict]:
        seen = set()
        output = []
        for item in items:
            key = item.get("url") or f"{item.get('source_type')}:{item.get('title')}"
            if key in seen:
                continue
            seen.add(key)
            output.append(item)
        return output

    @staticmethod
    def _summary(items: list[dict]) -> str:
        if not items:
            return "未检索到可用 PPT 补充资料。"
        return "\n".join([f"- [{item.get('source_type')}] {item.get('title')}: {item.get('snippet') or ''}" for item in items[:8]])
