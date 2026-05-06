from packages.agent.llm.openai_llm_client import OpenAILLMClient
from packages.agent.llm.prompt_loader import PromptLoader
from packages.agent.skills.base_skill import BaseSkill, SkillResult
from packages.shared.config import get_settings


class DocResearchPlanSkill(BaseSkill):
    name = "doc.plan_research"
    description = "根据文档大纲判断是否需要补充互联网或飞书内部文档资料。"

    def __init__(self):
        self.settings = get_settings()
        self.llm_client = OpenAILLMClient()

    async def run(self, params: dict, context) -> SkillResult:
        if not self.settings.research_enabled:
            plan = {
                "needs_research": False,
                "reason": "research disabled",
                "queries": [],
            }
            context.memory["research_plan"] = plan
            return SkillResult(success=True, message="资料检索已关闭", data={"research_plan": plan})

        summary = context.memory.get("discussion_summary", {})
        doc_outline = context.memory.get("doc_outline", {})
        task_goal = context.task.title

        try:
            plan = await self.llm_client.chat_json(
                system_prompt=PromptLoader.load("doc_research_plan_prompt.md"),
                user_prompt=(
                    f"用户任务目标：\n{task_goal}\n\n"
                    f"讨论总结：\n{summary}\n\n"
                    f"文档大纲：\n{doc_outline}\n\n"
                    "请判断是否需要资料检索。"
                ),
            )
        except Exception:
            plan = self._fallback_plan(task_goal, summary, doc_outline)

        normalized = self._normalize_plan(plan)
        context.memory["research_plan"] = normalized

        return SkillResult(
            success=True,
            message="已完成文档资料检索规划",
            data={"research_plan": normalized},
        )

    def _normalize_plan(self, plan: dict) -> dict:
        queries = []
        for query in (plan.get("queries") or [])[: self.settings.research_max_queries]:
            if not isinstance(query, dict):
                continue
            text = str(query.get("query") or "").strip()
            if not text:
                continue
            source = str(query.get("source") or "both").strip()
            if source not in {"web", "feishu_doc", "both"}:
                source = "both"
            queries.append(
                {
                    "section_id": str(query.get("section_id") or ""),
                    "query": text,
                    "source": source,
                    "purpose": str(query.get("purpose") or ""),
                }
            )

        return {
            "needs_research": bool(plan.get("needs_research") and queries),
            "reason": str(plan.get("reason") or ""),
            "queries": queries,
        }

    def _fallback_plan(self, task_goal: str, summary: dict, doc_outline: dict) -> dict:
        text = " ".join(
            [
                task_goal or "",
                str(summary.get("summary") or ""),
                " ".join(str(item) for item in summary.get("requirements", []) or []),
                " ".join(str(section.get("title") or "") for section in doc_outline.get("sections", []) or [] if isinstance(section, dict)),
            ]
        )
        keywords = ["查", "搜索", "调研", "参考", "竞品", "案例", "行业", "市场", "技术选型", "趋势"]
        if not any(keyword in text for keyword in keywords):
            return {
                "needs_research": False,
                "reason": "未识别到需要外部资料的章节或用户要求",
                "queries": [],
            }

        return {
            "needs_research": True,
            "reason": "识别到资料补充相关关键词",
            "queries": [
                {
                    "section_id": "",
                    "query": task_goal,
                    "source": "both",
                    "purpose": "补充文档背景和参考资料",
                }
            ],
        }
