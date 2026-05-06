from packages.agent.llm.openai_llm_client import OpenAILLMClient
from packages.agent.llm.prompt_loader import PromptLoader
from packages.agent.skills.base_skill import BaseSkill, SkillResult
from packages.shared.config import get_settings


class SlideResearchPlanSkill(BaseSkill):
    name = "slide.plan_research"
    description = "根据 PPT 大纲判断是否需要为演示稿补充资料。"

    def __init__(self):
        self.settings = get_settings()
        self.llm_client = OpenAILLMClient()

    async def run(self, params: dict, context) -> SkillResult:
        if not self.settings.research_enabled:
            plan = {"needs_research": False, "reason": "research disabled", "queries": []}
            context.memory["slide_research_plan"] = plan
            return SkillResult(success=True, message="PPT 资料检索已关闭", data={"slide_research_plan": plan})

        slide_outline = context.memory.get("slide_outline") or {}
        summary = context.memory.get("discussion_summary", {})

        try:
            plan = await self.llm_client.chat_json(
                system_prompt=PromptLoader.load("slide_research_plan_prompt.md"),
                user_prompt=(
                    f"任务目标：\n{context.task.title}\n\n"
                    f"讨论总结：\n{summary}\n\n"
                    f"PPT 大纲：\n{slide_outline}\n\n"
                    "请判断 PPT 是否需要补充资料。"
                ),
            )
        except Exception:
            plan = self._fallback_plan(context.task.title, slide_outline)

        normalized = self._normalize_plan(plan)
        context.memory["slide_research_plan"] = normalized

        return SkillResult(success=True, message="已完成 PPT 资料检索规划", data={"slide_research_plan": normalized})

    def _normalize_plan(self, plan: dict) -> dict:
        queries = []
        for query in (plan.get("queries") or [])[: self.settings.research_max_queries]:
            if not isinstance(query, dict):
                continue
            text = str(query.get("query") or "").strip()
            if not text:
                continue
            source = str(query.get("source") or "both")
            if source not in {"web", "feishu_doc", "both"}:
                source = "both"
            queries.append({"slide_id": str(query.get("slide_id") or ""), "query": text, "source": source, "purpose": str(query.get("purpose") or "")})

        return {"needs_research": bool(plan.get("needs_research") and queries), "reason": str(plan.get("reason") or ""), "queries": queries}

    @staticmethod
    def _fallback_plan(title: str, slide_outline: dict) -> dict:
        text = f"{title} {slide_outline}"
        keywords = ["竞品", "行业", "市场", "案例", "技术选型", "趋势", "数据", "调研", "参考"]
        if any(keyword in text for keyword in keywords):
            return {"needs_research": True, "reason": "识别到 PPT 资料补充关键词", "queries": [{"slide_id": "", "query": title, "source": "both", "purpose": "补充 PPT 参考资料"}]}
        return {"needs_research": False, "reason": "未识别到需要补充资料的 PPT 页面", "queries": []}
