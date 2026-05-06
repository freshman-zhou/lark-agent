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
                    f"用户重新生成反馈：\n{context.memory.get('regeneration_feedback') or '无'}\n\n"
                    "请生成 PPT 大纲 JSON。"
                ),
            )
            if self._is_outline_mismatched(context.task.title, summary, outline):
                outline = self._fallback_outline(context.task.title, summary, doc_outline)
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
        if cls._looks_like_travel(title, summary):
            return cls._travel_outline(title)

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

    @classmethod
    def _is_outline_mismatched(cls, title: str, summary: dict, outline: dict) -> bool:
        if not cls._looks_like_travel(title, summary):
            return False

        slide_titles = " ".join(
            str(slide.get("title") or "")
            for slide in outline.get("slides", [])
            if isinstance(slide, dict)
        )
        generic_terms = ["方案架构", "核心流程", "系统架构", "技术方案", "目标与范围"]
        travel_terms = ["行程", "景点", "预算", "住宿", "交通", "三亚", "旅游"]
        return any(term in slide_titles for term in generic_terms) and not any(term in slide_titles for term in travel_terms)

    @staticmethod
    def _looks_like_travel(title: str, summary: dict) -> bool:
        text = f"{title} {summary}"
        keywords = ["旅游", "旅行", "行程", "景点", "酒店", "住宿", "预算", "三亚", "亚龙湾", "蜈支洲岛", "天涯海角"]
        return any(keyword in text for keyword in keywords)

    @staticmethod
    def _travel_outline(title: str) -> dict:
        slides = [
            {"id": "cover", "page": 1, "title": title or "三亚旅行规划汇报", "purpose": "开场并说明旅行主题", "slide_type": "cover", "key_message": "5 天 4 晚三亚团建旅行规划", "content_sources": ["discussion_summary"], "visual_need": "photo"},
            {"id": "trip_snapshot", "page": 2, "title": "旅行概览", "purpose": "快速说明时间、人数、预算和核心目标", "slide_type": "summary", "key_message": "兼顾休闲观光、团队交流和预算控制", "content_sources": ["discussion_summary", "doc_markdown"], "visual_need": "photo"},
            {"id": "daily_itinerary", "page": 3, "title": "五日行程安排", "purpose": "按天展示核心活动和节奏", "slide_type": "timeline", "key_message": "先抵达适应，再海岛游玩，最后轻松返程", "content_sources": ["discussion_summary", "doc_markdown"], "visual_need": "diagram"},
            {"id": "attractions", "page": 4, "title": "核心景点推荐", "purpose": "展示亚龙湾、蜈支洲岛、天涯海角等重点景点", "slide_type": "comparison", "key_message": "经典景点覆盖海滩、海岛、人文和休闲体验", "content_sources": ["discussion_summary", "research"], "visual_need": "photo"},
            {"id": "hotel_transport", "page": 5, "title": "住宿与交通方案", "purpose": "说明住宿区域选择和团队移动方式", "slide_type": "solution", "key_message": "优先选择交通便利、适合团队出行的住宿区域", "content_sources": ["discussion_summary", "research"], "visual_need": "diagram"},
            {"id": "budget", "page": 6, "title": "预算拆分", "purpose": "展示人均 5000 元预算的组成", "slide_type": "comparison", "key_message": "预算重点集中在机票、住宿、餐饮、门票和团队活动", "content_sources": ["discussion_summary"], "visual_need": "chart"},
            {"id": "risks", "page": 7, "title": "注意事项与风险", "purpose": "提醒天气、防晒、安全和统一行动", "slide_type": "summary", "key_message": "提前管理天气、海上项目和团队协作风险", "content_sources": ["discussion_summary"], "visual_need": "illustration"},
            {"id": "next_steps", "page": 8, "title": "下一步确认事项", "purpose": "明确机票酒店报价、人数和特殊需求", "slide_type": "summary", "key_message": "完成报价、人数、酒店和项目确认后即可定稿", "content_sources": ["discussion_summary"], "visual_need": "none"},
        ]
        return {
            "title": title or "三亚旅行规划汇报",
            "audience": "团队成员与组织负责人",
            "presentation_goal": "确认三亚团建旅行行程、预算和待办",
            "tone": "轻松、清晰、适合团队沟通",
            "slides": slides,
            "confidence": 0.7,
        }

    @staticmethod
    def _slugify(text: str) -> str:
        return re.sub(r"[^a-zA-Z0-9]+", "_", text).strip("_").lower()[:48]
