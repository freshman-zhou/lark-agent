class MessageFilter:
    """群聊消息过滤器。

    第一版做轻量规则，避免把大量无效消息塞给 LLM。
    """

    USELESS_SHORT_MESSAGES = {
        "嗯",
        "好",
        "好的",
        "收到",
        "ok",
        "OK",
        "1",
        "是",
        "不是",
        "可以",
        "行",
    }

    def filter_messages(
        self,
        messages: list[dict],
        bot_sender_ids: set[str] | None = None,
    ) -> list[dict]:
        bot_sender_ids = bot_sender_ids or set()

        result = []
        seen_message_ids = set()

        for msg in messages:
            message_id = msg.get("message_id")
            sender_id = msg.get("sender_id")
            content = (msg.get("content") or "").strip()

            if not content:
                continue

            if message_id and message_id in seen_message_ids:
                continue

            if message_id:
                seen_message_ids.add(message_id)

            if sender_id and sender_id in bot_sender_ids:
                continue

            if len(content) <= 3 and content in self.USELESS_SHORT_MESSAGES:
                continue

            result.append(msg)

        return result