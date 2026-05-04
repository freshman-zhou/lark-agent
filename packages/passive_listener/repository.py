import hashlib
import uuid
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from packages.integrations.feishu.event.feishu_event_dto import FeishuMessageEventDTO
from packages.passive_listener.models import (
    ListenerChatMessageModel,
    ListenerDetectionRunModel,
    ListenerTaskSuggestionModel,
)


class ListenerDetectionStatus:
    RUNNING = "RUNNING"
    DETECTED = "DETECTED"
    NOT_DETECTED = "NOT_DETECTED"
    FAILED = "FAILED"


class ListenerSuggestionStatus:
    SUGGESTED = "SUGGESTED"
    CONFIRMED = "CONFIRMED"
    IGNORED = "IGNORED"
    EXPIRED = "EXPIRED"


class PassiveListenerRepository:
    def __init__(self, db: Session):
        self.db = db

    def create_chat_message(
        self,
        *,
        event: FeishuMessageEventDTO,
        triage_intent: str | None,
        triage_reason: str | None,
        signal_score: int,
        is_candidate: bool,
    ) -> tuple[ListenerChatMessageModel, bool]:
        model = ListenerChatMessageModel(
            id=f"lmsg_{uuid.uuid4().hex[:12]}",
            chat_id=event.chat_id,
            message_id=event.message_id,
            sender_id=event.sender_id,
            message_type=event.message_type,
            content=event.content,
            content_hash=self.hash_content(event.content),
            triage_intent=triage_intent,
            triage_reason=triage_reason,
            is_mention_bot=event.is_mention_bot,
            is_candidate=is_candidate,
            signal_score=signal_score,
            consumed=False,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )

        self.db.add(model)

        try:
            self.db.commit()
            self.db.refresh(model)
            return model, True
        except IntegrityError:
            self.db.rollback()
            existing = self.get_message_by_message_id(event.message_id)
            if existing is None:
                raise
            return existing, False

    def get_message_by_message_id(
        self,
        message_id: str,
    ) -> ListenerChatMessageModel | None:
        stmt = select(ListenerChatMessageModel).where(
            ListenerChatMessageModel.message_id == message_id
        )
        return self.db.scalar(stmt)

    def list_active_chat_ids(self, *, window_minutes: int) -> list[str]:
        since = datetime.utcnow() - timedelta(minutes=window_minutes)
        stmt = (
            select(ListenerChatMessageModel.chat_id)
            .where(ListenerChatMessageModel.created_at >= since)
            .distinct()
        )

        return [str(chat_id) for chat_id in self.db.execute(stmt).scalars().all()]

    def list_recent_messages(
        self,
        *,
        chat_id: str,
        window_minutes: int,
        limit: int,
    ) -> list[ListenerChatMessageModel]:
        since = datetime.utcnow() - timedelta(minutes=window_minutes)
        stmt = (
            select(ListenerChatMessageModel)
            .where(ListenerChatMessageModel.chat_id == chat_id)
            .where(ListenerChatMessageModel.created_at >= since)
            .order_by(ListenerChatMessageModel.created_at.desc())
            .limit(limit)
        )

        items = list(self.db.execute(stmt).scalars().all())
        items.reverse()
        return items

    def list_messages(
        self,
        *,
        chat_id: str | None = None,
        limit: int = 50,
    ) -> list[ListenerChatMessageModel]:
        stmt = select(ListenerChatMessageModel)

        if chat_id:
            stmt = stmt.where(ListenerChatMessageModel.chat_id == chat_id)

        stmt = stmt.order_by(ListenerChatMessageModel.created_at.desc()).limit(limit)
        return list(self.db.execute(stmt).scalars().all())

    def has_recent_detection(
        self,
        *,
        chat_id: str,
        cooldown_minutes: int,
    ) -> bool:
        since = datetime.utcnow() - timedelta(minutes=cooldown_minutes)
        stmt = (
            select(ListenerDetectionRunModel.id)
            .where(ListenerDetectionRunModel.chat_id == chat_id)
            .where(ListenerDetectionRunModel.created_at >= since)
            .limit(1)
        )
        return self.db.scalar(stmt) is not None

    def has_recent_suggestion(
        self,
        *,
        chat_id: str,
        cooldown_minutes: int,
    ) -> bool:
        since = datetime.utcnow() - timedelta(minutes=cooldown_minutes)
        stmt = (
            select(ListenerTaskSuggestionModel.id)
            .where(ListenerTaskSuggestionModel.chat_id == chat_id)
            .where(ListenerTaskSuggestionModel.created_at >= since)
            .where(ListenerTaskSuggestionModel.status == ListenerSuggestionStatus.SUGGESTED)
            .limit(1)
        )
        return self.db.scalar(stmt) is not None

    def get_detection_by_context_hash(
        self,
        context_hash: str,
    ) -> ListenerDetectionRunModel | None:
        stmt = select(ListenerDetectionRunModel).where(
            ListenerDetectionRunModel.context_hash == context_hash
        )
        return self.db.scalar(stmt)

    def get_detection_by_id(
        self,
        detection_id: str,
    ) -> ListenerDetectionRunModel | None:
        return self.db.get(ListenerDetectionRunModel, detection_id)

    def list_detections(
        self,
        *,
        chat_id: str | None = None,
        status: str | None = None,
        limit: int = 50,
    ) -> list[ListenerDetectionRunModel]:
        stmt = select(ListenerDetectionRunModel)

        if chat_id:
            stmt = stmt.where(ListenerDetectionRunModel.chat_id == chat_id)

        if status:
            stmt = stmt.where(ListenerDetectionRunModel.status == status)

        stmt = stmt.order_by(ListenerDetectionRunModel.created_at.desc()).limit(limit)
        return list(self.db.execute(stmt).scalars().all())

    def get_suggestion_by_context_hash(
        self,
        context_hash: str,
    ) -> ListenerTaskSuggestionModel | None:
        stmt = select(ListenerTaskSuggestionModel).where(
            ListenerTaskSuggestionModel.context_hash == context_hash
        )
        return self.db.scalar(stmt)

    def get_suggestion_by_id(
        self,
        suggestion_id: str,
    ) -> ListenerTaskSuggestionModel | None:
        return self.db.get(ListenerTaskSuggestionModel, suggestion_id)

    def list_suggestions(
        self,
        *,
        chat_id: str | None = None,
        status: str | None = None,
        limit: int = 50,
    ) -> list[ListenerTaskSuggestionModel]:
        stmt = select(ListenerTaskSuggestionModel)

        if chat_id:
            stmt = stmt.where(ListenerTaskSuggestionModel.chat_id == chat_id)

        if status:
            stmt = stmt.where(ListenerTaskSuggestionModel.status == status)

        stmt = stmt.order_by(ListenerTaskSuggestionModel.created_at.desc()).limit(limit)
        return list(self.db.execute(stmt).scalars().all())

    def create_detection_run(
        self,
        *,
        chat_id: str,
        context_hash: str,
        message_count: int,
        signal_score: int,
        trigger_reason: str,
        source_message_ids: list[str],
        llm_input_json: dict[str, Any] | None,
    ) -> tuple[ListenerDetectionRunModel, bool]:
        model = ListenerDetectionRunModel(
            id=f"ldet_{uuid.uuid4().hex[:12]}",
            chat_id=chat_id,
            context_hash=context_hash,
            status=ListenerDetectionStatus.RUNNING,
            message_count=message_count,
            signal_score=signal_score,
            trigger_reason=trigger_reason,
            source_message_ids=source_message_ids,
            llm_input_json=llm_input_json,
            llm_output_json=None,
            error_message=None,
            created_at=datetime.utcnow(),
            finished_at=None,
        )

        self.db.add(model)

        try:
            self.db.commit()
            self.db.refresh(model)
            return model, True
        except IntegrityError:
            self.db.rollback()
            existing = self.get_detection_by_context_hash(context_hash)
            if existing is None:
                raise
            return existing, False

    def finish_detection_run(
        self,
        *,
        detection_id: str,
        status: str,
        llm_output_json: dict[str, Any] | None = None,
        error_message: str | None = None,
    ) -> ListenerDetectionRunModel:
        model = self.db.get(ListenerDetectionRunModel, detection_id)
        if model is None:
            raise ValueError(f"Listener detection run not found: {detection_id}")

        model.status = status
        model.llm_output_json = llm_output_json
        model.error_message = error_message
        model.finished_at = datetime.utcnow()

        self.db.commit()
        self.db.refresh(model)
        return model

    def create_suggestion(
        self,
        *,
        chat_id: str,
        context_hash: str,
        task_type: str,
        task_title: str,
        suggested_command: str,
        confidence: float,
        reason: str | None,
        missing_info: list | None,
        suggested_deliverables: list | None,
        source_message_ids: list[str],
    ) -> tuple[ListenerTaskSuggestionModel, bool]:
        model = ListenerTaskSuggestionModel(
            id=f"lsug_{uuid.uuid4().hex[:12]}",
            chat_id=chat_id,
            context_hash=context_hash,
            task_type=task_type,
            task_title=task_title,
            suggested_command=suggested_command,
            confidence=confidence,
            reason=reason,
            missing_info=missing_info,
            suggested_deliverables=suggested_deliverables,
            source_message_ids=source_message_ids,
            status=ListenerSuggestionStatus.SUGGESTED,
            created_task_id=None,
            suggestion_card_message_id=None,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )

        self.db.add(model)

        try:
            self.db.commit()
            self.db.refresh(model)
            return model, True
        except IntegrityError:
            self.db.rollback()
            existing = self.get_suggestion_by_context_hash(context_hash)
            if existing is None:
                raise
            return existing, False

    def mark_suggestion_confirmed(
        self,
        *,
        suggestion_id: str,
        created_task_id: str,
    ) -> ListenerTaskSuggestionModel:
        model = self.get_suggestion_by_id(suggestion_id)
        if model is None:
            raise ValueError(f"Listener suggestion not found: {suggestion_id}")

        model.status = ListenerSuggestionStatus.CONFIRMED
        model.created_task_id = created_task_id
        model.updated_at = datetime.utcnow()

        self.db.commit()
        self.db.refresh(model)
        return model

    def mark_suggestion_ignored(
        self,
        *,
        suggestion_id: str,
    ) -> ListenerTaskSuggestionModel:
        model = self.get_suggestion_by_id(suggestion_id)
        if model is None:
            raise ValueError(f"Listener suggestion not found: {suggestion_id}")

        model.status = ListenerSuggestionStatus.IGNORED
        model.updated_at = datetime.utcnow()

        self.db.commit()
        self.db.refresh(model)
        return model

    def update_suggestion_card_message_id(
        self,
        *,
        suggestion_id: str,
        message_id: str,
    ) -> ListenerTaskSuggestionModel:
        model = self.get_suggestion_by_id(suggestion_id)
        if model is None:
            raise ValueError(f"Listener suggestion not found: {suggestion_id}")

        model.suggestion_card_message_id = message_id
        model.updated_at = datetime.utcnow()

        self.db.commit()
        self.db.refresh(model)
        return model

    def mark_messages_consumed(self, message_ids: list[str]) -> int:
        count = 0

        for message_id in message_ids:
            model = self.get_message_by_message_id(message_id)
            if model is None:
                continue

            model.consumed = True
            model.updated_at = datetime.utcnow()
            count += 1

        self.db.commit()
        return count

    @staticmethod
    def hash_content(content: str) -> str:
        return hashlib.sha256((content or "").encode("utf-8")).hexdigest()

    @staticmethod
    def build_context_hash(messages: list[ListenerChatMessageModel]) -> str:
        material = "\n".join(
            [
                f"{message.message_id}:{message.content_hash}"
                for message in messages
            ]
        )

        return hashlib.sha256(material.encode("utf-8")).hexdigest()
