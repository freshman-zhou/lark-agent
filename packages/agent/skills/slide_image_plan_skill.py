from packages.agent.llm.openai_llm_client import OpenAILLMClient
from packages.agent.llm.prompt_loader import PromptLoader
from packages.agent.skills.base_skill import BaseSkill, SkillResult


class SlideImagePlanSkill(BaseSkill):
    name = "slide.plan_images"
    description = "根据 PPT 大纲规划图片素材检索。"

    def __init__(self):
        self.llm_client = OpenAILLMClient()

    async def run(self, params: dict, context) -> SkillResult:
        slide_outline = context.memory.get("slide_outline") or {}

        try:
            plan = await self.llm_client.chat_json(
                system_prompt=PromptLoader.load("slide_image_plan_prompt.md"),
                user_prompt=f"PPT 大纲：\n{slide_outline}\n\n请规划图片素材检索。",
            )
        except Exception:
            plan = self._fallback_plan(slide_outline)

        normalized = self._normalize_plan(plan)
        context.memory["slide_image_plan"] = normalized

        return SkillResult(success=True, message="已完成 PPT 图片素材规划", data={"slide_image_plan": normalized})

    @staticmethod
    def _normalize_plan(plan: dict) -> dict:
        queries = []
        for query in (plan.get("queries") or [])[:3]:
            if not isinstance(query, dict):
                continue
            text = str(query.get("query") or "").strip()
            if text:
                queries.append({"slide_id": str(query.get("slide_id") or ""), "query": text, "purpose": str(query.get("purpose") or "")})
        return {"needs_images": bool(plan.get("needs_images") and queries), "reason": str(plan.get("reason") or ""), "queries": queries}

    @staticmethod
    def _fallback_plan(slide_outline: dict) -> dict:
        queries = []
        for slide in slide_outline.get("slides", []):
            visual = str(slide.get("visual_need") or "none")
            if visual not in {"none", ""} and len(queries) < 3:
                queries.append({"slide_id": slide.get("id") or "", "query": f"{slide.get('title')} {visual}", "purpose": "补充 PPT 视觉素材候选"})
        return {"needs_images": bool(queries), "reason": "根据 visual_need 自动规划图片检索", "queries": queries}
