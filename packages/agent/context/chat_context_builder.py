from packages.agent.context.message_filter import MessageFilter
from packages.shared.config import get_settings


class ChatContextBuilder:
    """把群聊消息整理成 LLM 可读上下文。"""

    def __init__(self):
        self.settings = get_settings()
        self.message_filter = MessageFilter()

    def build(
        self,
        messages: list[dict],
        task_goal: str,
        bot_sender_ids: set[str] | None = None,
    ) -> dict:
        filtered = self.message_filter.filter_messages(
            messages=messages,
            bot_sender_ids=bot_sender_ids,
        )

        lines = []
        for index, msg in enumerate(filtered, start=1):
            sender = msg.get("sender_id") or "unknown"
            time = msg.get("create_time") or ""
            content = msg.get("content") or ""

            lines.append(
                f"{index}. [{time}] {sender}: {content}"
            )

        context_text = "\n".join(lines)

        max_chars = self.settings.chat_context_max_chars
        if len(context_text) > max_chars:
            context_text = context_text[-max_chars:]

        return {
            "task_goal": task_goal,
            "message_count": len(filtered),
            "messages": filtered,
            "context_text": context_text,
        }