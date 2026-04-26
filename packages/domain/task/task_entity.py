from dataclasses import dataclass
from datetime import datetime
from typing import Any

from packages.domain.task.task_status import TaskStatus, TaskType, TaskSourceType

@dataclass
class TaskEntity:
    id: str
    title: str
    task_type: TaskType
    status: TaskStatus
    source_type: TaskSourceType
    source_chat_id: str | None
    source_message_id: str | None
    creator_id: str | None
    progress: int
    current_step: str
    plan_json: dict[str, Any] | None
    created_at: datetime
    updated_at: datetime