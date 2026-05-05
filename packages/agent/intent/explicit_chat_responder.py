import json

from packages.agent.llm.openai_llm_client import OpenAILLMClient
from packages.shared.config import get_settings


class ExplicitChatResponder:
    """Natural reply generator for @Agent messages that are not task requests."""

    SYSTEM_PROMPT = """你是 Agent-Pilot，一个团队协作场景里的办公助手。
用户已经 @ 了你，但当前消息没有被判定为创建任务。

请像正常同事一样简洁回复：
- 如果能回答，就直接回答。
- 如果用户像是在问某个上下文问题，可以结合 recent_chat_context 回答。
- 如果上下文不足，坦诚说明你现在只看到了有限上下文，并给出可操作的下一步。
- 不要强行创建任务，不要机械地说“没有识别到任务意图”。
- 如果用户其实可能想让你创建任务，可以温和询问是否要你整理成文档、PPT 或摘要。

回复 1-4 句话即可。"""

    def __init__(self):
        self.settings = get_settings()
        self.llm_client = OpenAILLMClient()

    async def reply(
        self,
        *,
        text: str,
        context_messages: list[dict] | None = None,
        reason: str | None = None,
    ) -> str:
        if not self.settings.explicit_chat_enable_llm:
            return self.fallback_reply(text)

        payload = {
            "message": text,
            "reason_not_task": reason,
            "recent_chat_context": context_messages or [],
        }

        return await self.llm_client.chat_text(
            system_prompt=self.SYSTEM_PROMPT,
            user_prompt=json.dumps(payload, ensure_ascii=False),
        )

    @staticmethod
    def fallback_reply(text: str) -> str:
        return (
            "我在。这个看起来不像一个需要我立刻创建的任务。\n"
            "如果你希望我继续推进，可以直接说：帮我整理成文档、生成 PPT，或者总结一下刚才讨论。"
        )
