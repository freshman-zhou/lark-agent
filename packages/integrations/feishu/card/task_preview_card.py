from typing import Any


class TaskPreviewCard:
    @staticmethod
    def build(
        task_id: str,
        title: str,
        task_type: str,
        preview: dict[str, Any],
    ) -> dict:
        deliverables = preview.get("deliverables", [])
        resources = preview.get("required_resources", [])
        steps = preview.get("execution_preview", [])
        questions = preview.get("clarifying_questions", [])

        deliverable_text = "\n".join([f"- {item}" for item in deliverables]) or "- 待确认"
        resource_text = "\n".join([f"- {item}" for item in resources]) or "- 当前用户指令"
        step_text = "\n".join(
            [
                f"{idx + 1}. {step.get('description') or step.get('name')}"
                for idx, step in enumerate(steps[:6])
            ]
        ) or "暂无执行步骤"
        question_text = "\n".join([f"- {item}" for item in questions]) or "- 暂无"

        return {
            "config": {
                "wide_screen_mode": True,
            },
            "header": {
                "template": "blue",
                "title": {
                    "tag": "plain_text",
                    "content": "Agent-Pilot 任务预览",
                },
            },
            "elements": [
                {
                    "tag": "div",
                    "text": {
                        "tag": "lark_md",
                        "content": (
                            f"**任务目标：**\n{title}\n\n"
                            f"**任务 ID：** `{task_id}`\n"
                            f"**任务类型：** `{task_type}`"
                        ),
                    },
                },
                {
                    "tag": "hr",
                },
                {
                    "tag": "div",
                    "text": {
                        "tag": "lark_md",
                        "content": f"**预计交付物：**\n{deliverable_text}",
                    },
                },
                {
                    "tag": "div",
                    "text": {
                        "tag": "lark_md",
                        "content": f"**需要使用的资源：**\n{resource_text}",
                    },
                },
                {
                    "tag": "div",
                    "text": {
                        "tag": "lark_md",
                        "content": f"**计划执行动作：**\n{step_text}",
                    },
                },
                {
                    "tag": "div",
                    "text": {
                        "tag": "lark_md",
                        "content": f"**可能需要确认的问题：**\n{question_text}",
                    },
                },
                {
                    "tag": "action",
                    "actions": [
                        {
                            "tag": "button",
                            "text": {
                                "tag": "plain_text",
                                "content": "确认执行",
                            },
                            "type": "primary",
                            "behaviors": [
                                {
                                    "type": "callback",
                                    "value": {
                                        "action": "confirm_task",
                                        "task_id": task_id,
                                    },
                                }
                            ],
                        },
                        {
                            "tag": "button",
                            "text": {
                                "tag": "plain_text",
                                "content": "取消任务",
                            },
                            "type": "default",
                            "behaviors": [
                                {
                                    "type": "callback",
                                    "value": {
                                        "action": "cancel_task",
                                        "task_id": task_id,
                                    },
                                }
                            ],
                        },
                    ],
                },
                {
                    "tag": "note",
                    "elements": [
                        {
                            "tag": "plain_text",
                            "content": "文本兜底：也可以在群里发送「确认 task_xxx」或「取消 task_xxx」。",
                        }
                    ],
                },
            ],
        }