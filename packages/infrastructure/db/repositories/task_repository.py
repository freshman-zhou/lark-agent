from sqlalchemy import select
from sqlalchemy.orm import Session
from packages.domain.task.task_entity import TaskEntity
from packages.domain.task.task_status import TaskStatus
from packages.infrastructure.db.models.task_model import TaskModel
from packages.shared.exceptions import NotFoundException


class TaskRepository:
    def __init__(self, db: Session):
        self.db = db

    def save(self, task: TaskEntity) -> TaskEntity:
        model = TaskModel(
            id=task.id,
            title=task.title,
            task_type=task.task_type,
            source_type=task.source_type,
            source_chat_id=task.source_chat_id,
            source_message_id=task.source_message_id,
            creator_id=task.creator_id,
            status=task.status.value if isinstance(task.status, TaskStatus) else str(task.status),
            progress=task.progress,
            current_step=task.current_step,
            plan_json=task.plan_json,
            created_at=task.created_at,
            updated_at=task.updated_at,
        )
        self.db.add(model)
        self.db.commit()
        self.db.refresh(model)
        return self._to_entity(model)

    def get_by_id(self, task_id: str) -> TaskEntity:
        model = self.db.get(TaskModel, task_id)
        if not model:
            raise NotFoundError(f"Task not found: {task_id}")
        return self._to_entity(model)

    def list_recent(self, limit: int = 20) -> list[TaskEntity]:
        stmt = select(TaskModel).order_by(TaskModel.created_at.desc()).limit(limit)
        return [self._to_entity(item) for item in self.db.execute(stmt).scalars().all()]

    def update_status(self, task_id: str, status: TaskStatus, current_step: str, progress: int | None = None) -> TaskEntity:
        model = self.db.get(TaskModel, task_id)
        if not model:
            raise NotFoundError(f"Task not found: {task_id}")
        model.status = status.value
        model.current_step = current_step
        if progress is not None:
            model.progress = progress
        self.db.commit()
        self.db.refresh(model)
        return self._to_entity(model)

    def update_plan(self, task_id: str, plan_json: dict) -> TaskEntity:
        model = self.db.get(TaskModel, task_id)
        if not model:
            raise NotFoundError(f"Task not found: {task_id}")
        model.plan_json = plan_json
        self.db.commit()
        self.db.refresh(model)
        return self._to_entity(model)

    @staticmethod
    def _to_entity(model: TaskModel) -> TaskEntity:
        return TaskEntity(
            id=model.id,
            title=model.title,
            task_type=model.task_type,
            source_type=model.source_type,
            source_chat_id=model.source_chat_id,
            source_message_id=model.source_message_id,
            creator_id=model.creator_id,
            status=TaskStatus(model.status),
            progress=model.progress,
            current_step=model.current_step,
            plan_json=model.plan_json,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )