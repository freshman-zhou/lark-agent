from pydantic import BaseModel, Field


class PlanStep(BaseModel):
    id: str
    name: str
    module: str
    need_confirm: bool = False


class TaskPlan(BaseModel):
    task_type: str
    summary: str
    steps: list[PlanStep] = Field(default_factory=list)
