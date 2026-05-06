from packages.agent.skills.base_skill import BaseSkill, SkillResult
from packages.agent.tools.tool_registry import ToolRegistry
from packages.shared.config import get_settings


class ImageSearchCollectSkill(BaseSkill):
    name = "image_search.collect"
    description = "按 slide_image_plan 检索 PPT 候选图片素材。"

    def __init__(self):
        self.settings = get_settings()
        self.tool_registry = ToolRegistry()

    async def run(self, params: dict, context) -> SkillResult:
        plan = context.memory.get("slide_image_plan") or {}
        if not plan.get("needs_images"):
            image_context = {"items": [], "summary": "本次 PPT 未触发图片检索。", "queries": []}
            context.memory["slide_image_context"] = image_context
            return SkillResult(success=True, message="无需检索 PPT 图片素材，已跳过", data={"slide_image_context": image_context})

        all_items = []
        query_results = []
        for query in plan.get("queries", [])[:3]:
            result = await self.tool_registry.run("image_search", query=query.get("query"), limit=self.settings.image_search_max_results_per_query)
            data = result.data or {}
            items = data.get("items") or []
            all_items.extend([{**item, "slide_id": query.get("slide_id") or "", "query": query.get("query"), "purpose": query.get("purpose") or ""} for item in items])
            query_results.append({"tool": "image_search", "query": query.get("query"), "success": result.success, "error": result.error, "item_count": len(items), "skipped": data.get("skipped")})

        image_context = {"items": all_items, "queries": query_results, "summary": self._summary(all_items)}
        context.memory["slide_image_context"] = image_context
        return SkillResult(success=True, message="已完成 PPT 图片素材检索", data={"slide_image_context": image_context})

    @staticmethod
    def _summary(items: list[dict]) -> str:
        if not items:
            return "未检索到可用 PPT 图片素材。"
        return "\n".join([f"- {item.get('title')}: {item.get('image_url')}" for item in items[:6]])
