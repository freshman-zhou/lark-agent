from typing import Any


class TaskStatusCard:
    @staticmethod
    def build(
        task_id: str,
        title: str,
        task_type: str,
        status: str,
        current_step: str,
        confirmed_by: str | None = None,
        confirmed_at: str | None = None,
        latest_job: dict[str, Any] | None = None,
        actions: list[dict[str, Any]] | None = None,
        delivery_result: dict[str, Any] | None = None,
        error_message: str | None = None,
        checkpoint_next: list[str] | None = None,
    ) -> dict:
        template = TaskStatusCard._template_by_status(status)
        status_title = TaskStatusCard._title_by_status(status)

        content = TaskStatusCard._build_main_content(
            task_id=task_id,
            title=title,
            task_type=task_type,
            status=status,
            current_step=current_step,
            confirmed_by=confirmed_by,
            confirmed_at=confirmed_at,
            latest_job=latest_job,
            delivery_result=delivery_result,
            error_message=error_message,
            checkpoint_next=checkpoint_next,
        )

        elements: list[dict[str, Any]] = [
            {
                "tag": "div",
                "text": {
                    "tag": "lark_md",
                    "content": content,
                },
            }
        ]

        recent_action_text = TaskStatusCard._recent_actions_text(actions or [])
        if recent_action_text:
            elements.append(
                {
                    "tag": "hr",
                }
            )
            elements.append(
                {
                    "tag": "div",
                    "text": {
                        "tag": "lark_md",
                        "content": recent_action_text,
                    },
                }
            )

        if status in {"WAITING_CONFIRM"}:
            elements.append(
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
                            "value": {
                                "action": "confirm_task",
                                "task_id": task_id,
                            },
                        },
                        {
                            "tag": "button",
                            "text": {
                                "tag": "plain_text",
                                "content": "取消任务",
                            },
                            "type": "default",
                            "value": {
                                "action": "cancel_task",
                                "task_id": task_id,
                            },
                        },
                    ],
                }
            )
        elif status in {"QUEUED", "RUNNING"}:
            elements.append(
                {
                    "tag": "note",
                    "elements": [
                        {
                            "tag": "plain_text",
                            "content": "任务正在后台执行，卡片会随执行进度自动刷新。",
                        }
                    ],
                }
            )
        elif status == "COMPLETED":
            elements.append(
                {
                    "tag": "note",
                    "elements": [
                        {
                            "tag": "plain_text",
                            "content": "任务已完成，请查看交付链接。",
                        }
                    ],
                }
            )
        elif status == "FAILED":
            elements.append(
                {
                    "tag": "note",
                    "elements": [
                        {
                            "tag": "plain_text",
                            "content": "任务执行失败，可查看失败原因后重新发起。",
                        }
                    ],
                }
            )

        return {
            "config": {
                "wide_screen_mode": True,
            },
            "header": {
                "template": template,
                "title": {
                    "tag": "plain_text",
                    "content": status_title,
                },
            },
            "elements": elements,
        }

    @staticmethod
    def _build_main_content(
        task_id: str,
        title: str,
        task_type: str,
        status: str,
        current_step: str,
        confirmed_by: str | None,
        confirmed_at: str | None,
        latest_job: dict[str, Any] | None,
        delivery_result: dict[str, Any] | None,
        error_message: str | None,
        checkpoint_next: list[str] | None,
    ) -> str:
        lines = [
            f"**任务：** {title}",
            f"**任务 ID：** `{task_id}`",
            f"**任务类型：** `{task_type}`",
            f"**状态：** `{status}`",
            f"**当前步骤：** {current_step}",
        ]

        if confirmed_by or confirmed_at:
            lines.append(f"**确认人：** {confirmed_by or '-'}")
            lines.append(f"**确认时间：** {confirmed_at or '-'}")

        if latest_job:
            lines.append("")
            lines.append(f"**Job：** `{latest_job.get('id')}`")
            lines.append(f"**Job 状态：** `{latest_job.get('status')}`")
            lines.append(
                f"**重试次数：** {latest_job.get('retry_count', 0)}"
                f"/{latest_job.get('max_retries', 0)}"
            )

        if checkpoint_next:
            lines.append(f"**LangGraph 下一节点：** `{', '.join(checkpoint_next)}`")

        delivery_text = TaskStatusCard._delivery_text(delivery_result)
        if delivery_text:
            lines.append("")
            lines.append(delivery_text)

        if error_message:
            lines.append("")
            lines.append("**失败原因：**")
            lines.append(error_message)

        return "\n".join(lines)

    @staticmethod
    def _recent_actions_text(actions: list[dict[str, Any]]) -> str:
        if not actions:
            return ""

        recent_actions = actions[-5:]
        lines = ["**最近执行记录：**"]

        for action in recent_actions:
            status = action.get("status") or "-"
            skill_name = action.get("skill_name") or action.get("action_name") or "-"
            duration = action.get("duration_ms")

            if duration is None:
                lines.append(f"- `{status}` {skill_name}")
            else:
                lines.append(f"- `{status}` {skill_name}，耗时 {duration} ms")

        return "\n".join(lines)

    @staticmethod
    def _delivery_text(delivery_result: dict[str, Any] | None) -> str:
        if not delivery_result:
            return ""

        doc_url = (
            delivery_result.get("doc_url")
            or delivery_result.get("document_url")
            or delivery_result.get("url")
        )
        slide_url = (
            delivery_result.get("slide_url")
            or delivery_result.get("ppt_url")
            or delivery_result.get("presentation_url")
        )

        lines = []

        if doc_url:
            lines.append(f"**文档链接：** {doc_url}")

        if slide_url:
            lines.append(f"**演示稿链接：** {slide_url}")

        return "\n".join(lines)

    @staticmethod
    def _template_by_status(status: str) -> str:
        if status in {"WAITING_CONFIRM", "QUEUED"}:
            return "blue"

        if status == "RUNNING":
            return "wathet"

        if status == "COMPLETED":
            return "green"

        if status == "FAILED":
            return "red"

        if status == "CANCELLED":
            return "grey"

        return "blue"

    @staticmethod
    def _title_by_status(status: str) -> str:
        mapping = {
            "WAITING_CONFIRM": "Agent-Pilot 任务待确认",
            "QUEUED": "Agent-Pilot 任务已确认，等待执行",
            "RUNNING": "Agent-Pilot 任务执行中",
            "COMPLETED": "Agent-Pilot 任务已完成",
            "FAILED": "Agent-Pilot 任务执行失败",
            "CANCELLED": "Agent-Pilot 任务已取消",
        }

        return mapping.get(status, "Agent-Pilot 任务状态")
    
    @staticmethod
    def _note_by_status(status: str) -> str:
        mapping = {
            "QUEUED": "任务已确认，正在等待 worker 领取。",
            "RUNNING": "任务正在后台执行，本卡片会持续更新执行阶段。",
            "COMPLETED": "任务已完成，请查看交付链接。",
            "FAILED": "任务执行失败，可根据失败原因重新发起。",
            "CANCELLED": "任务已取消。",
        }

        return mapping.get(status, "任务状态已更新。")