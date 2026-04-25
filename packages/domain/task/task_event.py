from datetime import datetime
from pydantic import BaseModel, Field


class TaskEvent(BaseModel):
    task_id: str
    actor_type: str
    action: str
    detail: dict = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)