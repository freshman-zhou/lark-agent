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
        for slide in outline.get("slides", []):
            slide_id = slide.get("id") or f"slide_{len(slides) + 1}"
            image_titles = [item.get("title") for item in image_context.get("items", []) if item.get("slide_id") == slide_id]
            slides.append(
                {
                    "id": slide_id,
                    "page": slide.get("page") or len(slides) + 1,
                    "type": slide.get("slide_type") or "generic",
                    "title": slide.get("title") or "未命名页面",
                    "subtitle": "" if slides else "基于飞书 IM 讨论自动生成",
                    "bullets": [slide.get("key_message") or slide.get("purpose") or summary.get("summary") or "待补充"],
                    "speaker_notes": slide.get("purpose") or "",
                    "visual_suggestion": {"type": "image" if image_titles else "none", "description": slide.get("visual_need") or "", "candidate_image_titles": image_titles[:3]},
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
