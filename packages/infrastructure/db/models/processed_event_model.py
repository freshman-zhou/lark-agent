from datetime import datetime

from sqlalchemy import DateTime, Index, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from packages.infrastructure.db.database import Base


class ProcessedEventModel(Base):
    __tablename__ = "processed_events"

    __table_args__ = (
        UniqueConstraint(
            "idempotency_key",
            name="uq_processed_events_idempotency_key",
        ),
        Index(
            "ix_processed_events_message_id",
            "message_id",
        ),
        Index(
            "ix_processed_events_chat_created_at",
            "chat_id",
            "created_at",
        ),
    )

    id: Mapped[str] = mapped_column(String(64), primary_key=True, index=True)
    idempotency_key: Mapped[str] = mapped_column(String(255), nullable=False)

    event_id: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    event_type: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    message_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    chat_id: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    sender_id: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)

    content_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    result_task_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    result_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )
