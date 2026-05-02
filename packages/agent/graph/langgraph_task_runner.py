# packages/agent/graph/langgraph_task_runner.py

from typing import Any

from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from sqlalchemy.orm import Session

from packages.agent.graph.checkpoint_config import (
    get_langgraph_checkpoint_db_path,
    get_langgraph_thread_id,
)
from packages.agent.graph.skill_node import ProgressCallback
from packages.agent.graph.task_graph import build_task_graph
from packages.domain.task.task_status import TaskStatus
from packages.infrastructure.db.repositories.agent_action_repository import (
    AgentActionRepository,
)
from packages.infrastructure.db.repositories.task_repository import TaskRepository
from packages.shared.logger import get_logger


logger = get_logger(__name__)


class LangGraphTaskRunner:
    """
    LangGraph 任务执行入口。

    现在支持 checkpoint：
    1. 每个 task_id 对应一个 thread_id；
    2. 图状态会持久化到 data/langgraph_checkpoints.sqlite；
    3. 如果存在未完成 checkpoint，则优先从 checkpoint 继续执行。
    """

    def __init__(
        self,
        db: Session,
        on_progress: ProgressCallback | None = None,
    ):
        self.db = db
        self.on_progress = on_progress
        self.task_repository = TaskRepository(db)
        self.action_repository = AgentActionRepository(db)
        self.checkpoint_db_path = get_langgraph_checkpoint_db_path()

    async def run(self, task_id: str) -> dict[str, Any]:
        thread_id = get_langgraph_thread_id(task_id)

        config = {
            "configurable": {
                "thread_id": thread_id,
            }
        }

        try:
            async with AsyncSqliteSaver.from_conn_string(
                self.checkpoint_db_path
            ) as checkpointer:
                graph = build_task_graph(
                    db=self.db,
                    on_progress=self.on_progress,
                    checkpointer=checkpointer,
                )

                graph_input = await self._build_graph_input(
                    graph=graph,
                    config=config,
                    task_id=task_id,
                )

                logger.info(
                    "Run LangGraph task: task_id=%s thread_id=%s resume=%s",
                    task_id,
                    thread_id,
                    graph_input is None,
                )

                result = await graph.ainvoke(
                    graph_input,
                    config=config,
                )

            actions = self.action_repository.list_by_task(task_id)
            status = result.get("status") or TaskStatus.COMPLETED.value

            return {
                "task_id": task_id,
                "thread_id": thread_id,
                "checkpoint_db_path": self.checkpoint_db_path,
                "status": status,
                "action_count": len(actions),
                "message": result.get("message") or "LangGraph 执行完成",
                "error": result.get("error"),
            }

        except Exception as exc:
            logger.exception(
                "LangGraphTaskRunner failed: task_id=%s error=%s",
                task_id,
                exc,
            )

            error_message = str(exc)

            try:
                self.db.rollback()
            except Exception:
                logger.exception("Rollback failed after LangGraph exception")

            try:
                self.task_repository.update_status(
                    task_id=task_id,
                    status=TaskStatus.FAILED,
                    current_step="LangGraph 执行异常",
                    progress=0,
                    error_message=error_message,
                )
            except Exception:
                logger.exception("Failed to update failed status: task_id=%s", task_id)

            return {
                "task_id": task_id,
                "thread_id": thread_id,
                "checkpoint_db_path": self.checkpoint_db_path,
                "status": TaskStatus.FAILED.value,
                "action_count": self._safe_action_count(task_id),
                "message": "LangGraph 执行异常",
                "error": error_message,
            }

    async def _build_graph_input(
        self,
        graph,
        config: dict[str, Any],
        task_id: str,
    ) -> dict[str, Any] | None:
        """
        判断是新执行还是从 checkpoint 恢复。

        - 如果 checkpoint 里存在 next 节点，说明图还没有跑完，可以传 None 继续。
        - 如果没有可继续节点，则传入新的初始 state。
        """
        try:
            snapshot = await graph.aget_state(config)

            next_nodes = tuple(getattr(snapshot, "next", ()) or ())

            if next_nodes:
                logger.info(
                    "Resume LangGraph from checkpoint: task_id=%s next=%s",
                    task_id,
                    next_nodes,
                )
                return None

        except Exception as exc:
            logger.warning(
                "Get checkpoint state failed, start from initial input: "
                "task_id=%s error=%s",
                task_id,
                exc,
            )

        return {
            "task_id": task_id,
            "memory": {},
            "executed_skill_names": [],
        }

    def _safe_action_count(self, task_id: str) -> int:
        try:
            return len(self.action_repository.list_by_task(task_id))
        except Exception:
            return 0