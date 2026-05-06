from datetime import datetime

from sqlalchemy import DateTime, Index, Integer, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from packages.infrastructure.db.database import Base


class ArtifactModel(Base):
    __tablename__ = "artifacts"

    __table_args__ = (
        UniqueConstraint(
            "task_id",
            "artifact_type",
            name="uq_artifacts_task_type",
        ),
        Index(
            "ix_artifacts_task_updated_at",
            "task_id",
            "updated_at",
        ),
    )

    id: Mapped[str] = mapped_column(String(64), primary_key=True, index=True)
    task_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    artifact_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    revision: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    content_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    source_action_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    last_edited_by: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    reviewed_by: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    feedback_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )
