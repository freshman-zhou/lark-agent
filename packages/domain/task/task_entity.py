from datetime import datetime
from pydantic import BaseModel, Field
from .task_status import TaskStatus


class TaskEntity(BaseModel):
    id: str
    title: str
    task_type: str
    source_type: str = "FEISHU_IM"
    source_chat_id: str | None = None
    source_message_id: str | None = None
    creator_id: str | None = None
    status: TaskStatus = TaskStatus.CREATED
    progress: int = 0
    current_step: str = "任务已创建"
    plan_json: dict | None = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)