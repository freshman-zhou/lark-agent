# packages/agent/graph/langgraph_task_runner.py

from typing import Any

from sqlalchemy.orm import Session

from packages.agent.graph.task_graph import build_task_graph
from packages.domain.task.task_status import TaskStatus
from packages.infrastructure.db.repositories.agent_action_repository import AgentActionRepository
from packages.infrastructure.db.repositories.task_repository import TaskRepository
from packages.shared.logger import get_logger

logger = get_logger(__name__)


class LangGraphTaskRunner:
    """
    LangGraph 任务执行入口。

    对外保持和原 AgentRuntime.run(task_id) 类似的接口，
    这样 application 层只需要替换一处调用。
    """

    def __init__(self, db: Session):
        self.db = db
        self.task_repository = TaskRepository(db)
        self.action_repository = AgentActionRepository(db)
        self.graph = build_task_graph(db)

    async def run(self, task_id: str) -> dict[str, Any]:
        try:
            result = await self.graph.ainvoke(
                {
                    "task_id": task_id,
                    "memory": {},
                    "executed_skill_names": [],
                },
                config={
                    "configurable": {
                        # 现在先不接 checkpointer，但提前按 task_id 传 thread_id，
                        # 后续接 LangGraph checkpoint 时可以无缝复用。
                        "thread_id": task_id,
                    }
                },
            )

            actions = self.action_repository.list_by_task(task_id)
            status = result.get("status") or TaskStatus.COMPLETED.value

            return {
                "task_id": task_id,
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
                "status": TaskStatus.FAILED.value,
                "action_count": self._safe_action_count(task_id),
                "message": "LangGraph 执行异常",
                "error": error_message,
            }

    def _safe_action_count(self, task_id: str) -> int:
        try:
            return len(self.action_repository.list_by_task(task_id))
        except Exception:
            return 0