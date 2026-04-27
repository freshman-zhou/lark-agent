from typing import Any


class TaskResultCard:
    @staticmethod
    def build(
        task_id: str,
        title: str,
        result: dict[str, Any],
    ) -> dict:
        doc_url = result.get("doc_url") or result.get("data", {}).get("doc_url") or "mock://feishu-doc-url"
        slide_url = result.get("slide_url") or result.get("data", {}).get("slide_url") or "mock://slide-preview-url"
        summary = result.get("summary") or result.get("message") or "任务已完成。"

        return {
            "config": {
                "wide_screen_mode": True,
            },
            "header": {
                "template": "green",
                "title": {
                    "tag": "plain_text",
                    "content": "Agent-Pilot 任务已完成",
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
                            f"**执行结果：**\n{summary}\n\n"
                            f"**方案文档：** {doc_url}\n"
                            f"**PPT 预览：** {slide_url}"
                        ),
                    },
                }
            ],
        }