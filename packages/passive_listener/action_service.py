from sqlalchemy.orm import Session

from packages.application.task_preview_service import TaskPreviewService
from packages.integrations.feishu.card.passive_task_suggestion_card import (
    PassiveTaskSuggestionCard,
)
from packages.integrations.feishu.im.message_api import FeishuMessageApi
from packages.passive_listener.repository import (
    ListenerSuggestionStatus,
    PassiveListenerRepository,
)


class PassiveSuggestionActionService:
    def __init__(self, db: Session):
        self.db = db
        self.repository = PassiveListenerRepository(db)
        self.task_preview_service = TaskPreviewService(db)
        self.message_api = FeishuMessageApi()

    async def create_task_preview(
        self,
        *,
        suggestion_id: str,
        operator_id: str | None = None,
        chat_id: str | None = None,
        card_message_id: str | None = None,
    ) -> dict:
        suggestion = self.repository.get_suggestion_by_id(suggestion_id)

        if suggestion is None:
            return {
                "ok": False,
                "message": "任务建议不存在",
            }

        if suggestion.status == ListenerSuggestionStatus.CONFIRMED:
            return {
                "ok": True,
                "message": "该建议已创建过任务预览",
                "task_id": suggestion.created_task_id,
            }

        if suggestion.status != ListenerSuggestionStatus.SUGGESTED:
            return {
                "ok": False,
                "message": f"当前建议状态不允许创建任务：{suggestion.status}",
            }

        target_chat_id = chat_id or suggestion.chat_id
        result = await self.task_preview_service.create_preview_from_passive_suggestion(
            chat_id=target_chat_id,
            suggestion_id=suggestion.id,
            command=suggestion.suggested_command,
            creator_id=operator_id,
        )

        task_id = result.get("task_id")
        self.repository.mark_suggestion_confirmed(
            suggestion_id=suggestion.id,
            created_task_id=task_id,
        )

        await self._update_suggestion_card(
            card_message_id=card_message_id or suggestion.suggestion_card_message_id,
            title="Agent-Pilot 已创建任务预览",
            content=(
                f"**建议已转为正式任务预览。**\n\n"
                f"任务 ID：`{task_id}`\n"
                "请在新的任务预览卡片中确认执行或取消。"
            ),
            template="green",
        )

        return {
            "ok": True,
            "message": "已创建任务预览",
            "task_id": task_id,
            "suggestion_id": suggestion.id,
            "result": result,
        }

    async def ignore_suggestion(
        self,
        *,
        suggestion_id: str,
        card_message_id: str | None = None,
    ) -> dict:
        suggestion = self.repository.get_suggestion_by_id(suggestion_id)

        if suggestion is None:
            return {
                "ok": False,
                "message": "任务建议不存在",
            }

        if suggestion.status == ListenerSuggestionStatus.IGNORED:
            return {
                "ok": True,
                "message": "该建议已忽略",
                "suggestion_id": suggestion.id,
            }

        self.repository.mark_suggestion_ignored(suggestion_id=suggestion.id)

        await self._update_suggestion_card(
            card_message_id=card_message_id or suggestion.suggestion_card_message_id,
            title="Agent-Pilot 任务建议已忽略",
            content=(
                "**已忽略这条任务建议。**\n\n"
                f"建议 ID：`{suggestion.id}`"
            ),
            template="grey",
        )

        return {
            "ok": True,
            "message": "已忽略任务建议",
            "suggestion_id": suggestion.id,
        }

    async def _update_suggestion_card(
        self,
        *,
        card_message_id: str | None,
        title: str,
        content: str,
        template: str,
    ) -> None:
        if not card_message_id:
            return

        card = PassiveTaskSuggestionCard.build_status(
            title=title,
            content=content,
            template=template,
        )

        try:
            await self.message_api.update_card_message(
                message_id=card_message_id,
                card=card,
            )
        except Exception:
            # Card update is best-effort. The action itself has already been
            # persisted and should not fail because of UI refresh.
            return
