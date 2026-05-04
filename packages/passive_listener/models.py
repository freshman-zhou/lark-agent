from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, Index, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from packages.infrastructure.db.database import Base


class ListenerChatMessageModel(Base):
    __tablename__ = "listener_chat_messages"

    __table_args__ = (
        Index(
            "ix_listener_chat_messages_chat_created_at",
            "chat_id",
            "created_at",
        ),
        Index(
            "ix_listener_chat_messages_message_id",
            "message_id",
            unique=True,
        ),
    )

    id: Mapped[str] = mapped_column(String(64), primary_key=True, index=True)
    chat_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    message_id: Mapped[str] = mapped_column(String(128), nullable=False)
    sender_id: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    message_type: Mapped[str | None] = mapped_column(String(32), nullable=True)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    triage_intent: Mapped[str | None] = mapped_column(String(64), nullable=True)
    triage_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_mention_bot: Mapped[bool] = mapped_column(Boolean, default=False)
    is_candidate: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    signal_score: Mapped[int] = mapped_column(Integer, default=0)
    consumed: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )


class ListenerDetectionRunModel(Base):
    __tablename__ = "listener_detection_runs"

    __table_args__ = (
        Index(
            "ix_listener_detection_runs_chat_created_at",
            "chat_id",
            "created_at",
        ),
        Index(
            "ix_listener_detection_runs_context_hash",
            "context_hash",
            unique=True,
        ),
    )

    id: Mapped[str] = mapped_column(String(64), primary_key=True, index=True)
    chat_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    context_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    message_count: Mapped[int] = mapped_column(Integer, default=0)
    signal_score: Mapped[int] = mapped_column(Integer, default=0)
    trigger_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_message_ids: Mapped[list | None] = mapped_column(JSON, nullable=True)
    llm_input_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    llm_output_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class ListenerTaskSuggestionModel(Base):
    __tablename__ = "listener_task_suggestions"

    __table_args__ = (
        Index(
            "ix_listener_task_suggestions_chat_created_at",
            "chat_id",
            "created_at",
        ),
        Index(
            "ix_listener_task_suggestions_context_hash",
            "context_hash",
            unique=True,
        ),
    )

    id: Mapped[str] = mapped_column(String(64), primary_key=True, index=True)
    chat_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    context_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    task_type: Mapped[str] = mapped_column(String(64), nullable=False)
    task_title: Mapped[str] = mapped_column(String(255), nullable=False)
    suggested_command: Mapped[str] = mapped_column(Text, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, default=0.0)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    missing_info: Mapped[list | None] = mapped_column(JSON, nullable=True)
    suggested_deliverables: Mapped[list | None] = mapped_column(JSON, nullable=True)
    source_message_ids: Mapped[list | None] = mapped_column(JSON, nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    created_task_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    suggestion_card_message_id: Mapped[str | None] = mapped_column(
        String(128),
        nullable=True,
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )
