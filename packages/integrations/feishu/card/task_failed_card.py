class TaskFailedCard:
    @staticmethod
    def build(
        task_id: str,
        title: str,
        error_message: str,
    ) -> dict:
        return {
            "config": {
                "wide_screen_mode": True,
            },
            "header": {
                "template": "red",
                "title": {
                    "tag": "plain_text",
                    "content": "Agent-Pilot 任务执行失败",
                },
            },
            "elements": [
                {
                    "tag": "div",
                    "text": {
                        "tag": "lark_md",
                        "content": (
                            f"**任务：** {title}\n"
                            f"**任务 ID：** `{task_id}`\n\n"
                            f"**失败原因：**\n{error_message}"
                        ),
                    },
                }
            ],
        }