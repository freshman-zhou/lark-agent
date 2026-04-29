from packages.agent.context.chat_context_builder import ChatContextBuilder
from packages.agent.skills.base_skill import BaseSkill, SkillResult
from packages.integrations.feishu.im.history_message_api import FeishuHistoryMessageApi
from packages.shared.config import get_settings


class FeishuCollectContextSkill(BaseSkill):
    name = "feishu.collect_chat_context"
    description = "根据 task.source_chat_id 拉取飞书群聊历史消息，并构造 LLM 可读上下文。"

    def __init__(self):
        self.settings = get_settings()
        self.history_api = FeishuHistoryMessageApi()
        self.context_builder = ChatContextBuilder()

    async def run(self, params: dict, context) -> SkillResult:
        chat_id = params.get("chat_id") or context.task.source_chat_id
        limit = params.get("limit") or self.settings.chat_context_limit

        if not chat_id:
            return SkillResult(
                success=False,
                error="chat_id is missing, cannot collect chat context",
            )

        messages = await self.history_api.list_chat_messages(
            chat_id=chat_id,
            page_size=limit,
        )

        built_context = self.context_builder.build(
            messages=messages,
            task_goal=context.task.title,
        )

        context.memory["chat_messages"] = built_context["messages"]
        context.memory["chat_context_text"] = built_context["context_text"]
        context.memory["chat_context"] = built_context

        return SkillResult(
            success=True,
            message="已收集真实飞书群聊上下文",
            data={
                "chat_id": chat_id,
                "message_count": built_context["message_count"],
                "messages": built_context["messages"],
                "context_text": built_context["context_text"],
            },
        )