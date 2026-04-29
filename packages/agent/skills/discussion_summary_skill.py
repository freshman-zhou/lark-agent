import json

from packages.agent.llm.openai_llm_client import OpenAILLMClient
from packages.agent.llm.prompt_loader import PromptLoader
from packages.agent.skills.base_skill import BaseSkill, SkillResult


class DiscussionSummarySkill(BaseSkill):
    name = "discussion.summarize"
    description = "调用 LLM 总结群聊讨论内容，输出需求、结论、分歧和待办。"

    def __init__(self):
        self.llm_client = OpenAILLMClient()

    async def run(self, params: dict, context) -> SkillResult:
        chat_context_text = context.memory.get("chat_context_text", "")
        task_goal = context.task.title

        if not chat_context_text:
            return SkillResult(
                success=False,
                error="chat_context_text is empty, please run feishu.collect_chat_context first",
            )

        system_prompt = PromptLoader.load("discussion_summary_prompt.md")

        user_prompt = (
            f"用户任务目标：\n{task_goal}\n\n"
            f"群聊上下文：\n{chat_context_text}\n\n"
            "请基于以上内容输出严格 JSON。"
        )

        summary = await self.llm_client.chat_json(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
        )

        normalized = self._normalize_summary(summary)

        context.memory["discussion_summary"] = normalized

        return SkillResult(
            success=True,
            message="已基于真实群聊内容生成结构化讨论总结",
            data={
                "summary": normalized,
            },
        )

    @staticmethod
    def _normalize_summary(summary: dict) -> dict:
        return {
            "summary": summary.get("summary", ""),
            "requirements": summary.get("requirements", []) or [],
            "decisions": summary.get("decisions", []) or [],
            "open_questions": summary.get("open_questions", []) or [],
            "todos": summary.get("todos", []) or [],
            "suggested_doc_outline": summary.get("suggested_doc_outline", []) or [],
            "suggested_slide_outline": summary.get("suggested_slide_outline", []) or [],
            "confidence": summary.get("confidence", 0),
            "raw": summary,
        }