from typing import Any

from packages.infrastructure.db.models.task_model import TaskModel
from packages.integrations.feishu.card.task_failed_card import TaskFailedCard
from packages.integrations.feishu.card.task_preview_card import TaskPreviewCard
from packages.integrations.feishu.card.task_progress_card import TaskProgressCard
from packages.integrations.feishu.card.task_result_card import TaskResultCard
from packages.integrations.feishu.im.message_api import FeishuMessageApi


class TaskNotifyService:
    def __init__(self):
        self.message_api = FeishuMessageApi()

    async def send_preview_by_reply(self, message_id: str, task: TaskModel) -> dict:
        card = TaskPreviewCard.build(
            task_id=task.id,
            title=task.title,
            task_type=task.task_type,
            preview=task.plan_json or {},
        )

        return await self.message_api.reply_card(
            message_id=message_id,
            card=card,
        )

    async def send_progress_to_chat(self, chat_id: str, task: TaskModel) -> dict:
        card = TaskProgressCard.build(
            task_id=task.id,
            title=task.title,
            status=task.status,
            current_step=task.current_step,
            progress=task.progress,
        )

        return await self.message_api.send_card_to_chat(
            chat_id=chat_id,
            card=card,
        )

    async def send_result_to_chat(
        self,
        chat_id: str,
        task: TaskModel,
        result: dict[str, Any],
    ) -> dict:
        card = TaskResultCard.build(
            task_id=task.id,
            title=task.title,
            result=result,
        )

        return await self.message_api.send_card_to_chat(
            chat_id=chat_id,
            card=card,
        )

    async def send_failed_to_chat(
        self,
        chat_id: str,
        task: TaskModel,
        error_message: str,
    ) -> dict:
        card = TaskFailedCard.build(
            task_id=task.id,
            title=task.title,
            error_message=error_message,
        )

        return await self.message_api.send_card_to_chat(
            chat_id=chat_id,
            card=card,
        )

    async def send_text_to_chat(self, chat_id: str, text: str) -> dict:
        return await self.message_api.send_text_to_chat(chat_id=chat_id, text=text)