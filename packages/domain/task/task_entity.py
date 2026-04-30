from dataclasses import dataclass, field
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
    progress: int
    created_at: datetime
    updated_at: datetime
    source_chat_id: str | None = None
    source_message_id: str | None = None
    creator_id: str | None = None
    confirmed_by: str | None = None
    confirmed_at: datetime | None = None
  
    current_step: str = "任务已创建"
    plan_json: dict[str, Any] | None = field(default_factory=dict)
    