from pydantic import BaseModel, Field


class PlanStep(BaseModel):
    name: str = Field(..., description="步骤名称")
    description: str = Field(..., description="步骤描述")
    tool: str = Field(..., description="后续执行该步骤需要调用的工具")
    need_confirm: bool = Field(default=False, description="该步骤是否需要用户确认")


class PlanResult(BaseModel):
    task_type: str
    title: str
    need_confirm: bool = True
    steps: list[PlanStep]