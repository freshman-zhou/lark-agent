# packages/agent/graph/skill_node.py

from typing import Any

from sqlalchemy.orm import Session

from packages.agent.graph.task_state import TaskGraphState
from packages.agent.runtime.agent_context import AgentContext
from packages.agent.skills.skill_registry import SkillRegistry
from packages.domain.task.task_status import TaskStatus
from packages.infrastructure.db.repositories.agent_action_repository import AgentActionRepository
from packages.infrastructure.db.repositories.task_repository import TaskRepository
from packages.shared.logger import get_logger

logger = get_logger(__name__)


class SkillNodeExecutor:
    """
    LangGraph 节点执行器。

    作用：
    1. 将原有 SkillRegistry.execute 包装成 LangGraph 节点；
    2. 继续复用 agent_actions 作为执行日志；
    3. 继续通过 tasks.status / current_step / progress 暴露任务进度。
    """

    def __init__(self, db: Session):
        self.db = db
        self.task_repository = TaskRepository(db)
        self.action_repository = AgentActionRepository(db)
        self.skill_registry = SkillRegistry()

    async def run_skill(
        self,
        state: TaskGraphState,
        *,
        skill_name: str,
        progress_after_success: int,
    ) -> TaskGraphState:
        task_id = state["task_id"]
        action_name = self._skill_to_action_name(skill_name)

        action = None

        try:
            task = self.task_repository.get_by_id(task_id)
            preview = state.get("preview") or task.plan_json or {}
            memory = dict(state.get("memory") or {})

            context = AgentContext(
                db=self.db,
                task=task,
                preview=preview,
                memory=memory,
            )

            action = self.action_repository.create_running(
                task_id=task_id,
                action_name=action_name,
                skill_name=skill_name,
                input_json={},
            )

            logger.info(
                "LangGraph run skill: task_id=%s skill=%s",
                task_id,
                skill_name,
            )

            result = await self.skill_registry.execute(
                skill_name=skill_name,
                params={},
                context=context,
            )

            output_json: dict[str, Any] = {
                "message": result.message,
                "data": result.data,
            }

            if not result.success:
                error_message = result.error or f"Skill failed: {skill_name}"

                self.action_repository.mark_failed(
                    action_id=action.id,
                    error_message=error_message,
                    output_json=output_json,
                )

                self.task_repository.update_status(
                    task_id=task_id,
                    status=TaskStatus.FAILED,
                    current_step=f"执行失败：{skill_name}",
                    progress=0,
                    error_message=error_message,
                )

                return {
                    **state,
                    "status": TaskStatus.FAILED.value,
                    "error": error_message,
                    "message": result.message or error_message,
                    "memory": context.memory,
                }

            self.action_repository.mark_success(
                action_id=action.id,
                output_json=output_json,
            )

            # Skill 内部已经可能写入 context.memory；
            # 这里再把 result.data 同步进去，兼容旧 AgentRuntime 的行为。
            if result.data:
                for key, value in result.data.items():
                    context.memory[key] = value

            executed_skill_names = list(state.get("executed_skill_names") or [])
            executed_skill_names.append(skill_name)

            self.task_repository.update_status(
                task_id=task_id,
                status=TaskStatus.RUNNING,
                current_step=f"已完成：{skill_name}",
                progress=progress_after_success,
            )

            return {
                **state,
                "status": TaskStatus.RUNNING.value,
                "current_step": f"已完成：{skill_name}",
                "progress": progress_after_success,
                "memory": context.memory,
                "executed_skill_names": executed_skill_names,
                "error": None,
                "message": result.message,
            }

        except Exception as exc:
            logger.exception(
                "LangGraph skill node failed: task_id=%s skill=%s error=%s",
                task_id,
                skill_name,
                exc,
            )

            try:
                self.db.rollback()
            except Exception:
                logger.exception("Rollback failed after skill node exception")

            error_message = str(exc)

            if action is not None:
                try:
                    self.action_repository.mark_failed(
                        action_id=action.id,
                        error_message=error_message,
                        output_json={"error": error_message},
                    )
                except Exception:
                    logger.exception("Failed to mark action failed")

            try:
                self.task_repository.update_status(
                    task_id=task_id,
                    status=TaskStatus.FAILED,
                    current_step=f"执行异常：{skill_name}",
                    progress=0,
                    error_message=error_message,
                )
            except Exception:
                logger.exception("Failed to update task failed status")

            return {
                **state,
                "status": TaskStatus.FAILED.value,
                "error": error_message,
                "message": error_message,
            }

    @staticmethod
    def _skill_to_action_name(skill_name: str) -> str:
        return skill_name.replace(".", "_")