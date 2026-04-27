class TaskProgressCard:
    @staticmethod
    def build(
        task_id: str,
        title: str,
        status: str,
        current_step: str,
        progress: int,
    ) -> dict:
        return {
            "config": {
                "wide_screen_mode": True,
            },
            "header": {
                "template": "wathet",
                "title": {
                    "tag": "plain_text",
                    "content": "Agent-Pilot 任务执行中",
                },
            },
            "elements": [
                {
                    "tag": "div",
                    "text": {
                        "tag": "lark_md",
                        "content": (
                            f"**任务：** {title}\n"
                            f"**任务 ID：** `{task_id}`\n"
                            f"**状态：** `{status}`\n"
                            f"**当前步骤：** {current_step}\n"
                            f"**进度：** {progress}%"
                        ),
                    },
                }
            ],
        }