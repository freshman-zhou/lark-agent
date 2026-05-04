from typing import Any

from sqlalchemy.orm import Session

from packages.passive_listener.repository import PassiveListenerRepository


class PassiveListenerViewService:
    def __init__(self, db: Session):
        self.repository = PassiveListenerRepository(db)

    def list_messages(
        self,
        *,
        chat_id: str | None = None,
        limit: int = 50,
    ) -> dict[str, Any]:
        items = self.repository.list_messages(chat_id=chat_id, limit=limit)

        return {
            "items": [self._serialize_message(item) for item in items],
            "count": len(items),
        }

    def list_detections(
        self,
        *,
        chat_id: str | None = None,
        status: str | None = None,
        limit: int = 50,
    ) -> dict[str, Any]:
        items = self.repository.list_detections(
            chat_id=chat_id,
            status=status,
            limit=limit,
        )

        return {
            "items": [self._serialize_detection(item) for item in items],
            "count": len(items),
        }

    def get_detection(self, detection_id: str) -> dict[str, Any]:
        item = self.repository.get_detection_by_id(detection_id)
        if item is None:
            raise ValueError(f"Listener detection not found: {detection_id}")

        return self._serialize_detection(item)

    def list_suggestions(
        self,
        *,
        chat_id: str | None = None,
        status: str | None = None,
        limit: int = 50,
    ) -> dict[str, Any]:
        items = self.repository.list_suggestions(
            chat_id=chat_id,
            status=status,
            limit=limit,
        )

        return {
            "items": [self._serialize_suggestion(item) for item in items],
            "count": len(items),
        }

    def get_suggestion(self, suggestion_id: str) -> dict[str, Any]:
        item = self.repository.get_suggestion_by_id(suggestion_id)
        if item is None:
            raise ValueError(f"Listener suggestion not found: {suggestion_id}")

        return self._serialize_suggestion(item)

    @staticmethod
    def _serialize_message(item) -> dict[str, Any]:
        return {
            "id": item.id,
            "chat_id": item.chat_id,
            "message_id": item.message_id,
            "sender_id": item.sender_id,
            "message_type": item.message_type,
            "content": item.content,
            "content_hash": item.content_hash,
            "triage_intent": item.triage_intent,
            "triage_reason": item.triage_reason,
            "is_mention_bot": item.is_mention_bot,
            "is_candidate": item.is_candidate,
            "signal_score": item.signal_score,
            "consumed": item.consumed,
            "created_at": PassiveListenerViewService._dt(item.created_at),
            "updated_at": PassiveListenerViewService._dt(item.updated_at),
        }

    @staticmethod
    def _serialize_detection(item) -> dict[str, Any]:
        return {
            "id": item.id,
            "chat_id": item.chat_id,
            "context_hash": item.context_hash,
            "status": item.status,
            "message_count": item.message_count,
            "signal_score": item.signal_score,
            "trigger_reason": item.trigger_reason,
            "source_message_ids": item.source_message_ids,
            "llm_input_json": item.llm_input_json,
            "llm_output_json": item.llm_output_json,
            "error_message": item.error_message,
            "created_at": PassiveListenerViewService._dt(item.created_at),
            "finished_at": PassiveListenerViewService._dt(item.finished_at),
        }

    @staticmethod
    def _serialize_suggestion(item) -> dict[str, Any]:
        return {
            "id": item.id,
            "chat_id": item.chat_id,
            "context_hash": item.context_hash,
            "task_type": item.task_type,
            "task_title": item.task_title,
            "suggested_command": item.suggested_command,
            "confidence": item.confidence,
            "reason": item.reason,
            "missing_info": item.missing_info,
            "suggested_deliverables": item.suggested_deliverables,
            "source_message_ids": item.source_message_ids,
            "status": item.status,
            "created_task_id": item.created_task_id,
            "suggestion_card_message_id": item.suggestion_card_message_id,
            "created_at": PassiveListenerViewService._dt(item.created_at),
            "updated_at": PassiveListenerViewService._dt(item.updated_at),
        }

    @staticmethod
    def _dt(value) -> str | None:
        if value is None:
            return None

        return value.isoformat()
