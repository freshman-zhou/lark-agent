# packages/application/task_checkpoint_view_service.py

from typing import Any

from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from sqlalchemy.orm import Session

from packages.agent.graph.checkpoint_config import (
    get_langgraph_checkpoint_db_path,
    get_langgraph_thread_id,
)
from packages.agent.graph.task_graph import build_task_graph


class TaskCheckpointViewService:
    def __init__(self, db: Session):
        self.db = db
        self.checkpoint_db_path = get_langgraph_checkpoint_db_path()

    async def get_checkpoint_state(self, task_id: str) -> dict[str, Any]:
        thread_id = get_langgraph_thread_id(task_id)

        config = {
            "configurable": {
                "thread_id": thread_id,
            }
        }

        async with AsyncSqliteSaver.from_conn_string(
            self.checkpoint_db_path
        ) as checkpointer:
            graph = build_task_graph(
                db=self.db,
                checkpointer=checkpointer,
            )

            snapshot = await graph.aget_state(config)

        values = getattr(snapshot, "values", None)
        next_nodes = getattr(snapshot, "next", None)
        snapshot_config = getattr(snapshot, "config", None)
        parent_config = getattr(snapshot, "parent_config", None)
        metadata = getattr(snapshot, "metadata", None)
        created_at = getattr(snapshot, "created_at", None)

        return {
            "task_id": task_id,
            "thread_id": thread_id,
            "checkpoint_db_path": self.checkpoint_db_path,
            "has_checkpoint": bool(values or next_nodes or snapshot_config),
            "values": values or {},
            "next": list(next_nodes or []),
            "config": snapshot_config,
            "parent_config": parent_config,
            "metadata": metadata,
            "created_at": self._serialize_datetime(created_at),
        }

    @staticmethod
    def _serialize_datetime(value: Any) -> str | None:
        if value is None:
            return None

        if isinstance(value, str):
            return value

        if hasattr(value, "isoformat"):
            return value.isoformat()

        return str(value)
