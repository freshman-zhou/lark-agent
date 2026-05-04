from typing import Any


class PassiveTaskSuggestionCard:
    @staticmethod
    def build(
        *,
        suggestion_id: str,
        task_title: str,
        task_type: str,
        suggested_command: str,
        confidence: float,
        reason: str | None = None,
        missing_info: list | None = None,
        suggested_deliverables: list | None = None,
    ) -> dict[str, Any]:
        confidence_text = f"{confidence:.2f}"
        deliverable_text = "\n".join(
            [f"- {item}" for item in suggested_deliverables or []]
        ) or "- 待确认"
        missing_text = "\n".join(
            [f"- {item}" for item in missing_info or []]
        ) or "- 暂无"

        return {
            "config": {
                "wide_screen_mode": True,
            },
            "header": {
                "template": "wathet",
                "title": {
                    "tag": "plain_text",
                    "content": "Agent-Pilot 发现可能任务",
                },
            },
            "elements": [
                {
                    "tag": "div",
                    "text": {
                        "tag": "lark_md",
                        "content": (
                            "**我观察到最近讨论可能需要沉淀成任务：**\n\n"
                            f"**可能目标：** {task_title}\n"
                            f"**任务类型：** `{task_type}`\n"
                            f"**置信度：** {confidence_text}\n\n"
                            f"**建议交付：**\n{deliverable_text}\n\n"
                            f"**依据：** {reason or '-'}\n\n"
                            f"**待确认：**\n{missing_text}\n\n"
                            f"**建议指令：**\n{suggested_command}"
                        ),
                    },
                },
                {
                    "tag": "action",
                    "actions": [
                        {
                            "tag": "button",
                            "text": {
                                "tag": "plain_text",
                                "content": "创建任务预览",
                            },
                            "type": "primary",
                            "behaviors": [
                                {
                                    "type": "callback",
                                    "value": {
                                        "action": "create_task_preview_from_suggestion",
                                        "suggestion_id": suggestion_id,
                                    },
                                }
                            ],
                        },
                        {
                            "tag": "button",
                            "text": {
                                "tag": "plain_text",
                                "content": "忽略",
                            },
                            "type": "default",
                            "behaviors": [
                                {
                                    "type": "callback",
                                    "value": {
                                        "action": "ignore_task_suggestion",
                                        "suggestion_id": suggestion_id,
                                    },
                                }
                            ],
                        },
                    ],
                },
            ],
        }

    @staticmethod
    def build_status(
        *,
        title: str,
        content: str,
        template: str = "green",
    ) -> dict[str, Any]:
        return {
            "config": {
                "wide_screen_mode": True,
            },
            "header": {
                "template": template,
                "title": {
                    "tag": "plain_text",
                    "content": title,
                },
            },
            "elements": [
                {
                    "tag": "div",
                    "text": {
                        "tag": "lark_md",
                        "content": content,
                    },
                }
            ],
        }
