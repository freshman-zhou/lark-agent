from packages.integrations.feishu.card.passive_task_suggestion_card import (
    PassiveTaskSuggestionCard,
)
from packages.integrations.feishu.im.message_api import FeishuMessageApi
from packages.passive_listener.models import ListenerTaskSuggestionModel
from packages.passive_listener.repository import PassiveListenerRepository
from packages.shared.logger import get_logger


logger = get_logger(__name__)


class PassiveSuggestionNotifyService:
    def __init__(self, repository: PassiveListenerRepository):
        self.repository = repository
        self.message_api = FeishuMessageApi()

    async def send_suggestion_card(
        self,
        suggestion: ListenerTaskSuggestionModel,
    ) -> dict | None:
        if suggestion.suggestion_card_message_id:
            return None

        card = PassiveTaskSuggestionCard.build(
            suggestion_id=suggestion.id,
            task_title=suggestion.task_title,
            task_type=suggestion.task_type,
            suggested_command=suggestion.suggested_command,
            confidence=suggestion.confidence,
            reason=suggestion.reason,
            missing_info=suggestion.missing_info,
            suggested_deliverables=suggestion.suggested_deliverables,
        )

        response = await self.message_api.send_card_to_chat(
            chat_id=suggestion.chat_id,
            card=card,
        )

        message_id = FeishuMessageApi.extract_message_id(response)
        if message_id:
            self.repository.update_suggestion_card_message_id(
                suggestion_id=suggestion.id,
                message_id=message_id,
            )

        logger.info(
            "Passive suggestion card sent: suggestion_id=%s message_id=%s",
            suggestion.id,
            message_id,
        )

        return response
