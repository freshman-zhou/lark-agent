from datetime import datetime
from pydantic import BaseModel, Field


class TaskStep(BaseModel):
    id: str
    task_id: str
    name: str
    step_type: str
    status: str = "PENDING"
    input_json: dict | None = None
    output_json: dict | None = None
    error_message: str | None = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)