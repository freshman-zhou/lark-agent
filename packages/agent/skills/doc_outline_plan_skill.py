import re

from packages.agent.llm.openai_llm_client import OpenAILLMClient
from packages.agent.llm.prompt_loader import PromptLoader
from packages.agent.skills.base_skill import BaseSkill, SkillResult


class DocOutlinePlanSkill(BaseSkill):
    name = "doc.plan_outline"
    description = "根据讨论总结动态规划云文档大纲，并预留协作确认节点。"

    def __init__(self):
        self.llm_client = OpenAILLMClient()

    async def run(self, params: dict, context) -> SkillResult:
        summary = context.memory.get("discussion_summary", {})
        task_goal = context.task.title

        system_prompt = PromptLoader.load("doc_outline_prompt.md")
        user_prompt = (
            f"用户任务目标：\n{task_goal}\n\n"
            f"结构化讨论总结：\n{summary}\n\n"
            f"用户重新生成反馈：\n{context.memory.get('regeneration_feedback') or '无'}\n\n"
            "请输出动态文档大纲 JSON。"
        )

        try:
            outline = await self.llm_client.chat_json(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
            )
        except Exception:
            outline = self._fallback_outline(task_goal, summary)

        normalized = self._normalize_outline(task_goal, outline)

        context.memory["doc_outline"] = normalized
        context.memory["doc_outline_status"] = "PLANNED"
        context.memory["collaboration_checkpoints"] = normalized.get(
            "collaboration_checkpoints",
            [],
        )

        return SkillResult(
            success=True,
            message="已根据讨论内容生成动态文档大纲",
            data={
                "doc_outline": normalized,
                "doc_outline_status": "PLANNED",
            },
        )

    @classmethod
    def _normalize_outline(cls, task_goal: str, outline: dict) -> dict:
        sections = outline.get("sections") or []
        normalized_sections = []

        for index, section in enumerate(sections[:8], start=1):
            if not isinstance(section, dict):
                continue

            title = str(section.get("title") or "").strip()
            if not title:
                continue

            section_id = str(section.get("id") or cls._slugify(title) or f"section_{index}")
            normalized_sections.append(
                {
                    "id": section_id,
                    "title": title,
                    "purpose": str(section.get("purpose") or "").strip(),
                    "format": cls._normalize_format(section.get("format")),
                    "key_points": section.get("key_points") or [],
                }
            )

        if not normalized_sections:
            fallback = cls._fallback_outline(task_goal, {})
            normalized_sections = fallback["sections"]

        return {
            "title": str(outline.get("title") or task_goal or "方案文档").strip(),
            "doc_type": str(outline.get("doc_type") or "unknown"),
            "sections": normalized_sections,
            "collaboration_checkpoints": outline.get("collaboration_checkpoints")
            or [
                {
                    "stage": "outline_confirm",
                    "description": "等待用户确认大纲",
                    "auto_confirm": True,
                },
                {
                    "stage": "draft_review",
                    "description": "等待用户编辑初稿",
                    "auto_confirm": True,
                },
            ],
            "confidence": float(outline.get("confidence") or 0),
        }

    @staticmethod
    def _normalize_format(value) -> str:
        allowed = {"paragraph", "bullets", "table", "checklist"}
        text = str(value or "paragraph").strip()
        return text if text in allowed else "paragraph"

    @classmethod
    def _fallback_outline(cls, task_goal: str, summary: dict) -> dict:
        suggested = summary.get("suggested_doc_outline") or []
        sections = []

        for index, title in enumerate(suggested[:6], start=1):
            title_text = str(title).strip()
            if title_text:
                sections.append(
                    {
                        "id": cls._slugify(title_text) or f"section_{index}",
                        "title": title_text,
                        "purpose": "根据讨论总结补充本章节内容",
                        "format": "paragraph",
                        "key_points": [],
                    }
                )

        if not sections:
            sections = [
                {
                    "id": "background",
                    "title": "背景与目标",
                    "purpose": "说明讨论背景、业务目标和文档目标",
                    "format": "paragraph",
                    "key_points": [],
                },
                {
                    "id": "requirements",
                    "title": "核心需求",
                    "purpose": "整理群聊中明确提出的需求",
                    "format": "bullets",
                    "key_points": [],
                },
                {
                    "id": "decisions",
                    "title": "已确认结论",
                    "purpose": "沉淀已达成一致的方案结论",
                    "format": "bullets",
                    "key_points": [],
                },
                {
                    "id": "open_questions",
                    "title": "待确认问题",
                    "purpose": "列出需要继续澄清的问题",
                    "format": "checklist",
                    "key_points": [],
                },
            ]

        return {
            "title": task_goal or "方案文档",
            "doc_type": "unknown",
            "sections": sections,
            "collaboration_checkpoints": [
                {
                    "stage": "outline_confirm",
                    "description": "等待用户确认大纲",
                    "auto_confirm": True,
                },
                {
                    "stage": "draft_review",
                    "description": "等待用户编辑初稿",
                    "auto_confirm": True,
                },
            ],
            "confidence": 0,
        }

    @staticmethod
    def _slugify(text: str) -> str:
        slug = re.sub(r"[^a-zA-Z0-9]+", "_", text).strip("_").lower()
        return slug[:48]
