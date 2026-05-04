import hashlib
import uuid
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from packages.infrastructure.db.models.processed_event_model import ProcessedEventModel
from packages.integrations.feishu.event.feishu_event_dto import FeishuMessageEventDTO


class ProcessedEventStatus:
    PROCESSING = "PROCESSING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    IGNORED = "IGNORED"


class ProcessedEventRepository:
    def __init__(self, db: Session):
        self.db = db

    def begin_message_event(
        self,
        event: FeishuMessageEventDTO,
    ) -> tuple[ProcessedEventModel, bool]:
        """Try to claim a message event.

        Returns (record, created). created=False means this event/message has
        already been seen and should not create side effects again.
        """
        idempotency_key = self.build_idempotency_key(event)

        record = ProcessedEventModel(
            id=f"evt_{uuid.uuid4().hex[:12]}",
            idempotency_key=idempotency_key,
            event_id=event.event_id,
            event_type=event.event_type,
            message_id=event.message_id,
            chat_id=event.chat_id,
            sender_id=event.sender_id,
            content_hash=self.hash_content(event.content),
            status=ProcessedEventStatus.PROCESSING,
            result_task_id=None,
            result_message=None,
            error_message=None,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )

        self.db.add(record)

        try:
            self.db.commit()
            self.db.refresh(record)
            return record, True
        except IntegrityError:
            self.db.rollback()
            existing = self.get_by_idempotency_key(idempotency_key)
            if existing is None:
                raise
            return existing, False

    def mark_success(
        self,
        event_id: str,
        *,
        result_task_id: str | None = None,
        result_message: str | None = None,
    ) -> ProcessedEventModel:
        return self._mark_finished(
            event_id=event_id,
            status=ProcessedEventStatus.SUCCESS,
            result_task_id=result_task_id,
            result_message=result_message,
            error_message=None,
        )

    def mark_ignored(
        self,
        event_id: str,
        *,
        result_message: str | None = None,
    ) -> ProcessedEventModel:
        return self._mark_finished(
            event_id=event_id,
            status=ProcessedEventStatus.IGNORED,
            result_task_id=None,
            result_message=result_message,
            error_message=None,
        )

    def mark_failed(
        self,
        event_id: str,
        *,
        error_message: str,
    ) -> ProcessedEventModel:
        return self._mark_finished(
            event_id=event_id,
            status=ProcessedEventStatus.FAILED,
            result_task_id=None,
            result_message=None,
            error_message=error_message,
        )

    def get_by_idempotency_key(self, idempotency_key: str) -> ProcessedEventModel | None:
        stmt = select(ProcessedEventModel).where(
            ProcessedEventModel.idempotency_key == idempotency_key
        )
        return self.db.scalar(stmt)

    def _mark_finished(
        self,
        *,
        event_id: str,
        status: str,
        result_task_id: str | None,
        result_message: str | None,
        error_message: str | None,
    ) -> ProcessedEventModel:
        record = self.db.get(ProcessedEventModel, event_id)

        if record is None:
            raise ValueError(f"Processed event not found: {event_id}")

        record.status = status
        record.result_task_id = result_task_id
        record.result_message = result_message
        record.error_message = error_message
        record.updated_at = datetime.utcnow()

        self.db.commit()
        self.db.refresh(record)

        return record

    @staticmethod
    def build_idempotency_key(event: FeishuMessageEventDTO) -> str:
        # 对消息事件优先使用 message_id：同一条飞书消息即使被重新包装成
        # 不同事件投递，也只能触发一次业务副作用。
        if event.message_id:
            return f"feishu:message:{event.message_id}"

        if event.event_id:
            return f"feishu:event:{event.event_id}"

        content_hash = ProcessedEventRepository.hash_content(event.content)
        return f"feishu:content:{event.chat_id}:{event.sender_id}:{content_hash}"

    @staticmethod
    def hash_content(content: str) -> str:
        return hashlib.sha256((content or "").encode("utf-8")).hexdigest()
