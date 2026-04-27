from dataclasses import dataclass
from typing import Any

from sqlalchemy.orm import Session

from packages.infrastructure.db.models.task_model import TaskModel


@dataclass
class AgentContext:
    db: Session
    task: TaskModel
    preview: dict[str, Any]
    memory: dict[str, Any]