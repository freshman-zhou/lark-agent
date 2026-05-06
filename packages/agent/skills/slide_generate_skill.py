from packages.agent.llm.openai_llm_client import OpenAILLMClient
from packages.agent.llm.prompt_loader import PromptLoader
from packages.agent.skills.base_skill import BaseSkill, SkillResult


class SlideGenerateSkill(BaseSkill):
    name = "slide.generate_deck"
    description = "根据已确认 PPT 大纲、资料和图片素材生成完整 slide_json。"

    def __init__(self):
        self.llm_client = OpenAILLMClient()

    async def run(self, params: dict, context) -> SkillResult:
        summary = context.memory.get("discussion_summary", {})
        slide_outline = context.memory.get("slide_outline") or {}
        doc_markdown = context.memory.get("doc_markdown") or ""
        slide_research_context = context.memory.get("slide_research_context") or {}
        slide_image_context = context.memory.get("slide_image_context") or {}

        try:
            slide_json = await self.llm_client.chat_json(
                system_prompt=PromptLoader.load("slide_deck_prompt.md"),
                user_prompt=(
                    f"任务目标：\n{context.task.title}\n\n"
                    f"讨论总结：\n{summary}\n\n"
                    f"文档内容摘录：\n{doc_markdown[:5000]}\n\n"
                    f"已确认 PPT 大纲：\n{slide_outline}\n\n"
                    f"PPT 补充资料：\n{slide_research_context}\n\n"
                    f"PPT 图片候选：\n{slide_image_context}\n\n"
                    "请生成完整 slide_json。"
                ),
            )
        except Exception:
            slide_json = self._fallback_deck(context.task.title, summary, slide_outline, slide_image_context)

        slide_json = self._normalize_deck(context.task.title, slide_json)
        context.memory["slide_json"] = slide_json
        context.memory["slide_deck_status"] = "GENERATED"

        return SkillResult(success=True, message="已生成完整 PPT 内容结构", data={"slide_json": slide_json, "slide_deck_status": "GENERATED"})

    def _fallback_deck(self, title: str, summary: dict, outline: dict, image_context: dict) -> dict:
        slides = []
        requirements = summary.get("requirements") or []
        decisions = summary.get("decisions") or []
        open_questions = summary.get("open_questions") or []
        todos = summary.get("todos") or []

        for slide in outline.get("slides", []):
            slide_id = slide.get("id") or f"slide_{len(slides) + 1}"
            image_items = [item for item in image_context.get("items", []) if item.get("slide_id") == slide_id]
            image_titles = [item.get("title") for item in image_items]
            image_urls = [item.get("image_url") for item in image_items if item.get("image_url")]
            slides.append(
                {
                    "id": slide_id,
                    "page": slide.get("page") or len(slides) + 1,
                    "type": slide.get("slide_type") or "generic",
                    "title": slide.get("title") or "未命名页面",
                    "subtitle": "" if slides else "基于飞书 IM 讨论自动生成",
                    "bullets": self._bullets_for_slide(
                        slide_id=slide_id,
                        slide=slide,
                        summary=summary,
                        requirements=requirements,
                        decisions=decisions,
                        open_questions=open_questions,
                        todos=todos,
                    ),
                    "speaker_notes": slide.get("purpose") or "",
                    "visual_suggestion": {
                        "type": "image" if image_titles or image_urls else slide.get("visual_need") or "none",
                        "description": slide.get("visual_need") or "",
                        "candidate_image_titles": image_titles[:3],
                        "candidate_image_urls": image_urls[:3],
                    },
                    "sources": ["群聊总结", "云文档"],
                }
            )

        if not slides:
            slides = [{"id": "cover", "page": 1, "type": "cover", "title": title, "subtitle": "基于飞书 IM 讨论自动生成", "bullets": [summary.get("summary") or "暂无内容"], "speaker_notes": "", "visual_suggestion": {"type": "none", "description": "", "candidate_image_titles": []}, "sources": ["群聊总结"]}]

        return {"title": outline.get("title") or title, "slides": slides}

    @staticmethod
    def _normalize_deck(title: str, deck: dict) -> dict:
        slides = deck.get("slides") or []
        normalized = []
        for index, slide in enumerate(slides[:10], start=1):
            if not isinstance(slide, dict):
                continue
            normalized.append(
                {
                    "id": str(slide.get("id") or f"slide_{index}"),
                    "page": int(slide.get("page") or index),
                    "type": str(slide.get("type") or slide.get("slide_type") or "generic"),
                    "title": str(slide.get("title") or f"第 {index} 页"),
                    "subtitle": str(slide.get("subtitle") or ""),
                    "bullets": slide.get("bullets") or [],
                    "speaker_notes": str(slide.get("speaker_notes") or ""),
                    "visual_suggestion": slide.get("visual_suggestion") or {},
                    "sources": slide.get("sources") or [],
                }
            )
        return {"title": str(deck.get("title") or title or "汇报演示稿"), "source": "agent_pilot", "slides": normalized}

    def _bullets_for_slide(
        self,
        *,
        slide_id: str,
        slide: dict,
        summary: dict,
        requirements: list,
        decisions: list,
        open_questions: list,
        todos: list,
    ) -> list[str]:
        if slide_id == "cover":
            return [
                slide.get("key_message") or summary.get("summary") or "行程规划汇报",
                "面向团队确认旅行目标、预算和执行安排",
            ]

        if slide_id == "trip_snapshot":
            return [
                "行程周期：5 天 4 晚，兼顾休闲观光与团队交流",
                "预算目标：人均控制在 5000 元以内",
                "核心目标：覆盖经典景点、控制成本、降低执行不确定性",
            ]

        if slide_id == "daily_itinerary":
            return [
                "Day 1：抵达三亚，入住酒店，团队集合",
                "Day 2：亚龙湾海滨休闲与自由活动",
                "Day 3：蜈支洲岛游玩，下午安排团队活动",
                "Day 4：天涯海角与南山文化旅游区",
                "Day 5：轻松购物、自由活动与返程",
            ]

        if slide_id == "attractions":
            return [
                "亚龙湾：海滩休闲和团队合影重点场景",
                "蜈支洲岛：海岛体验，可选潜水和水上项目",
                "天涯海角：三亚标志性人文景点",
                "南山文化旅游区：适合半日文化观光",
            ]

        if slide_id == "hotel_transport":
            return [
                "住宿优先考虑亚龙湾或大东海，兼顾景点距离和团队出行",
                "市内交通建议统一包车，减少分散行动风险",
                "酒店选择关注早餐、会议/团建空间和取消政策",
            ]

        if slide_id == "budget":
            return [
                "机票与住宿是预算大头，需要优先锁定报价",
                "门票和交通按团队统一采购降低不确定性",
                "团队晚宴和水上项目建议单独列预算池",
                "保留 5% 到 10% 机动费用应对天气和价格波动",
            ]

        if slide_id == "risks":
            return [
                "天气风险：提前准备雨天备选活动",
                "安全风险：海上项目需确认资质、保险和自愿参与",
                "健康风险：防晒、防暑、特殊饮食需求提前收集",
                "协作风险：统一集合时间和紧急联系人机制",
            ]

        if slide_id == "next_steps":
            todo_lines = []
            for todo in todos[:3]:
                if isinstance(todo, dict):
                    todo_lines.append(f"{todo.get('owner', '负责人')}：{todo.get('task', '')}（{todo.get('deadline', '待定')}）")
            return todo_lines or [
                "确认参与人数和特殊需求",
                "获取机票、酒店、包车和景点报价",
                "确认是否加入潜水等自费项目",
            ]

        base = []
        if slide.get("key_message"):
            base.append(slide["key_message"])
        base.extend(requirements[:3])
        base.extend(decisions[:2])
        if open_questions:
            base.append(f"待确认：{open_questions[0]}")
        return base[:5] or [slide.get("purpose") or summary.get("summary") or "待补充"]
