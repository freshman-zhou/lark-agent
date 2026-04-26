from uuid import uuid4
from datetime import datetime

from sqlalchemy.orm import Session
from packages.agent.nodes.intent_router_node import IntentRouterNode
from packages.agent.nodes.planner_node import PlannerNode
from packages.domain.task.task_entity import TaskEntity
from packages.domain.task.task_status import TaskSourceType, TaskStatus, TaskType
from packages.infrastructure.db.repositories.task_repository import TaskRepository
from packages.shared.exceptions import TaskNotFoundException

class TaskService:
    def __init__(self, db: Session):
        self.repo = TaskRepository(db)
        self.intent_router = IntentRouterNode()
        self.planner = PlannerNode()

    def create_from_feishu_message(
        self,
        content: str,
        chat_id: str,
        message_id: str,
        creator_id: str,
    ) -> TaskEntity:
        plan = self.planner.plan(content)
        task_type = TaskType(plan.task_type)
        now = datetime.utcnow()

        task = TaskEntity(
            id=f"task_{uuid4().hex[:12]}",
            title=plan.title[:255] or content[:255] or "未命名任务",
            task_type=task_type,
            source_type=TaskSourceType.FEISHU_IM,
            source_chat_id=chat_id,
            source_message_id=message_id,
            creator_id=creator_id,
            status=TaskStatus.CREATED,
            progress=0,
            current_step="任务已创建，等待进入规划流程",
            plan_json=plan.model_dump(),
            created_at=now,
            updated_at=now,
        )
        return self.repo.save(task)

    
    def get_task(self, task_id: str) -> TaskEntity:
        task = self.repo.get_by_id(task_id)
        if task is None:
            raise TaskNotFoundException(task_id)
        return task

    def list_recent_tasks(self, limit: int = 20) -> list[TaskEntity]:
        return self.repo.list_recent(limit)
