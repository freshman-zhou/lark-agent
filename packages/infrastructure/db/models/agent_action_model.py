from datetime import datetime

from sqlalchemy import DateTime, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from packages.infrastructure.db.database import Base


class AgentActionModel(Base):
    __tablename__ = "agent_actions"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, index=True)

    task_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)

    sequence: Mapped[int] = mapped_column(Integer, nullable=False)

    action_name: Mapped[str] = mapped_column(String(128), nullable=False)
    skill_name: Mapped[str] = mapped_column(String(128), nullable=False)

    status: Mapped[str] = mapped_column(String(64), nullable=False)

    input_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    output_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    started_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
    )

    finished_at: Mapped[datetime | None] = mapped_column(
        DateTime,
        nullable=True,
    )