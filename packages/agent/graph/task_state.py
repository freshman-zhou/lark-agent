# packages/agent/graph/task_state.py

from typing import Any, TypedDict


class TaskGraphState(TypedDict, total=False):
    task_id: str

    title: str
    task_type: str
    status: str

    preview: dict[str, Any]
    memory: dict[str, Any]
    executed_skill_names: list[str]

    current_step: str
    progress: int

    error: str | None
    message: str | None