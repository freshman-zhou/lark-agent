from sqlalchemy.orm import Session

from packages.agent.executor.agent_executor import AgentExecutor
from packages.agent.runtime.agent_context import AgentContext
from packages.agent.skills.skill_registry import SkillRegistry
from packages.domain.task.task_status import TaskStatus
from packages.infrastructure.db.repositories.agent_action_repository import AgentActionRepository
from packages.infrastructure.db.repositories.task_repository import TaskRepository
from packages.shared.exceptions import TaskNotFoundException
from packages.shared.logger import get_logger

logger = get_logger(__name__)


class AgentRuntime:
    """Agent 任务运行时。

    职责：
    1. 加载 task 和 preview
    2. 让 AgentExecutor 决定下一步 skill
    3. 通过 SkillRegistry 执行 skill
    4. 记录 agent_action
    5. 更新 task 状态
    """

    def __init__(self, db: Session):
        self.db = db
        self.task_repository = TaskRepository(db)
        self.action_repository = AgentActionRepository(db)
        self.executor = AgentExecutor()
        self.skill_registry = SkillRegistry()
    
    # v1模拟简单的任务执行，后续改为agent自主规划
    async def run(self, task_id: str) -> dict:
        task = self.task_repository.get_by_id(task_id)

        if task is None:
            raise TaskNotFoundException(task_id)

        task_status = self._normalize_status(task.status)

        if task_status not in {
            TaskStatus.CONFIRMED,
            TaskStatus.RUNNING,
            TaskStatus.WAITING_CONFIRM,
        }:
            return {
                "task_id": task_id,
                "status": task_status.value,
                "message": "当前任务状态不允许启动 AgentRuntime",
            }

        self.task_repository.update_status(
            task_id=task_id,
            status=TaskStatus.RUNNING,
            current_step="Agent 正在执行任务",
            progress=10,
        )

        preview = task.plan_json or {}
        context = AgentContext(
            db=self.db,
            task=task,
            preview=preview,
            memory={},
        )

        executed_skill_names: list[str] = []

        try:
            while True:
                next_action = self.executor.decide_next_action(
                    preview=preview,
                    executed_skill_names=executed_skill_names,
                )

                if next_action.finish:
                    break

                action = self.action_repository.create_running(
                    task_id=task_id,
                    action_name=next_action.action_name,
                    skill_name=next_action.skill_name,
                    input_json=next_action.params,
                )

                logger.info(
                    "Run agent action: task_id=%s skill=%s",
                    task_id,
                    next_action.skill_name,
                )

                result = await self.skill_registry.execute(
                    skill_name=next_action.skill_name,
                    params=next_action.params,
                    context=context,
                )

                if not result.success:
                    self.action_repository.mark_failed(
                        action_id=action.id,
                        error_message=result.error or "Skill execution failed",
                        output_json={
                            "message": result.message,
                            "data": result.data,
                        },
                    )

                    self.task_repository.update_status(
                        task_id=task_id,
                        status=TaskStatus.FAILED,
                        current_step=f"执行失败：{next_action.skill_name}",
                        progress=0,
                        error_message=result.error,
                    )

                    return {
                        "task_id": task_id,
                        "status": TaskStatus.FAILED.value,
                        "error": result.error,
                    }

                output_json = {
                    "message": result.message,
                    "data": result.data,
                }

                self.action_repository.mark_success(
                    action_id=action.id,
                    output_json=output_json,
                )

                if result.data:
                    # 常用输出同步进 memory，供后续 skill 使用
                    for key, value in result.data.items():
                        context.memory[key] = value

                executed_skill_names.append(next_action.skill_name)

                progress = min(90, 10 + len(executed_skill_names) * 20)

                self.task_repository.update_status(
                    task_id=task_id,
                    status=TaskStatus.RUNNING,
                    current_step=f"已完成：{next_action.skill_name}",
                    progress=progress,
                )

            self.task_repository.update_status(
                task_id=task_id,
                status=TaskStatus.COMPLETED,
                current_step="任务已完成",
                progress=100,
            )

            actions = self.action_repository.list_by_task(task_id)

            return {
                "task_id": task_id,
                "status": TaskStatus.COMPLETED.value,
                "action_count": len(actions),
                "message": "AgentRuntime 执行完成",
            }

        except Exception as exc:
            logger.exception("AgentRuntime failed: task_id=%s error=%s", task_id, exc)

            self.task_repository.update_status(
                task_id=task_id,
                status=TaskStatus.FAILED,
                current_step="AgentRuntime 执行异常",
                progress=0,
                error_message=str(exc),
            )

            return {
                "task_id": task_id,
                "status": TaskStatus.FAILED.value,
                "error": str(exc),
            }

    @staticmethod
    def _normalize_status(status: TaskStatus | str) -> TaskStatus:
        if isinstance(status, TaskStatus):
            return status
        return TaskStatus(status)
