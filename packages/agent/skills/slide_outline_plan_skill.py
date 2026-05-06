import re

from packages.agent.llm.openai_llm_client import OpenAILLMClient
from packages.agent.llm.prompt_loader import PromptLoader
from packages.agent.skills.base_skill import BaseSkill, SkillResult


class SlideOutlinePlanSkill(BaseSkill):
    name = "slide.plan_outline"
    description = "根据讨论总结和云文档内容动态规划 PPT 大纲。"

    def __init__(self):
        self.llm_client = OpenAILLMClient()

    async def run(self, params: dict, context) -> SkillResult:
        summary = context.memory.get("discussion_summary", {})
        doc_outline = context.memory.get("doc_outline") or {}
        doc_markdown = context.memory.get("doc_markdown") or ""

        try:
            outline = await self.llm_client.chat_json(
                system_prompt=PromptLoader.load("slide_outline_prompt.md"),
                user_prompt=(
                    f"任务目标：\n{context.task.title}\n\n"
                    f"讨论总结：\n{summary}\n\n"
                    f"文档大纲：\n{doc_outline}\n\n"
                    f"文档内容摘录：\n{doc_markdown[:5000]}\n\n"
                    "请生成 PPT 大纲 JSON。"
                ),
            )
        except Exception:
            outline = self._fallback_outline(context.task.title, summary, doc_outline)

        normalized = self._normalize_outline(context.task.title, outline)
        context.memory["slide_outline"] = normalized
        context.memory["slide_outline_status"] = "PLANNED"

        return SkillResult(
            success=True,
            message="已生成动态 PPT 大纲",
            data={"slide_outline": normalized, "slide_outline_status": "PLANNED"},
        )

    @classmethod
    def _normalize_outline(cls, title: str, outline: dict) -> dict:
        slides = []
        for index, slide in enumerate((outline.get("slides") or [])[:10], start=1):
            if not isinstance(slide, dict):
                continue
            slide_title = str(slide.get("title") or "").strip()
            if not slide_title:
                continue
            slides.append(
                {
                    "id": str(slide.get("id") or cls._slugify(slide_title) or f"slide_{index}"),
                    "page": int(slide.get("page") or index),
                    "title": slide_title,
                    "purpose": str(slide.get("purpose") or ""),
                    "slide_type": str(slide.get("slide_type") or "generic"),
                    "key_message": str(slide.get("key_message") or ""),
                    "content_sources": slide.get("content_sources") or [],
                    "visual_need": str(slide.get("visual_need") or "none"),
                }
            )

        if not slides:
            fallback = cls._fallback_outline(title, {}, {})
            slides = fallback["slides"]

        return {
            "title": str(outline.get("title") or title or "汇报演示稿"),
            "audience": str(outline.get("audience") or "团队成员"),
            "presentation_goal": str(outline.get("presentation_goal") or "汇报方案与进展"),
            "tone": str(outline.get("tone") or "清晰、专业"),
            "slides": slides,
            "collaboration_checkpoints": outline.get("collaboration_checkpoints")
            or [
                {"stage": "slide_outline_confirm", "description": "等待用户确认 PPT 大纲", "auto_confirm": True},
                {"stage": "slide_deck_review", "description": "等待用户确认完整 PPT", "auto_confirm": True},
            ],
            "confidence": float(outline.get("confidence") or 0),
        }

    @classmethod
    def _fallback_outline(cls, title: str, summary: dict, doc_outline: dict) -> dict:
        suggested = summary.get("suggested_slide_outline") or []
        slides = [{"id": "cover", "page": 1, "title": title or "汇报演示稿", "purpose": "开场", "slide_type": "cover", "key_message": "", "content_sources": ["discussion_summary"], "visual_need": "none"}]

        if suggested:
            for index, item in enumerate(suggested[:7], start=2):
                slide_title = str(item)
                slides.append({"id": cls._slugify(slide_title) or f"slide_{index}", "page": index, "title": slide_title, "purpose": "展示关键内容", "slide_type": "generic", "key_message": slide_title, "content_sources": ["discussion_summary"], "visual_need": "none"})
        else:
            defaults = [
                ("background", "背景与痛点", "problem", "illustration"),
                ("goals", "目标与范围", "solution", "none"),
                ("architecture", "方案架构", "architecture", "diagram"),
                ("workflow", "核心流程", "solution", "diagram"),
                ("plan", "后续计划", "timeline", "none"),
                ("summary", "总结", "summary", "none"),
            ]
            for index, (sid, stitle, stype, visual) in enumerate(defaults, start=2):
                slides.append({"id": sid, "page": index, "title": stitle, "purpose": "展示关键内容", "slide_type": stype, "key_message": "", "content_sources": ["discussion_summary", "doc_markdown"], "visual_need": visual})

        return {"title": title or "汇报演示稿", "slides": slides}

    @staticmethod
    def _slugify(text: str) -> str:
        return re.sub(r"[^a-zA-Z0-9]+", "_", text).strip("_").lower()[:48]
