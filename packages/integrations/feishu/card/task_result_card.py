from typing import Any


class TaskResultCard:
    @staticmethod
    def build(
        task_id: str,
        title: str,
        result: dict[str, Any],
    ) -> dict:
        doc_url = result.get("doc_url") or result.get("data", {}).get("doc_url")
        slide_url = result.get("slide_url") or result.get("data", {}).get("slide_url")
        summary = result.get("summary") or result.get("message") or "任务已完成。"
        result_lines = [
            f"**任务：** {title}",
            f"**任务 ID：** `{task_id}`",
            "",
            f"**执行结果：**\n{summary}",
        ]

        if doc_url:
            result_lines.extend(["", f"**方案文档：** {doc_url}"])

        if slide_url:
            result_lines.append(f"**PPT 预览：** {slide_url}")

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
                        "content": "\n".join(result_lines),
                    },
                }
            ],
        }
