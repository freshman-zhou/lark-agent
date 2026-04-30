from datetime import datetime
from sqlalchemy import select,update
from sqlalchemy.orm import Session
from packages.domain.task.task_entity import TaskEntity
from packages.domain.task.task_status import TaskSourceType, TaskStatus, TaskType
from packages.infrastructure.db.models.task_model import TaskModel
from packages.shared.exceptions import NotFoundException


class TaskRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, task: TaskModel) -> TaskModel:
        self.db.add(task)
        self.db.commit()
        self.db.refresh(task)
        return task

    def save(self, task: TaskEntity) -> TaskEntity:
        model = TaskModel(
            id=task.id,
            title=task.title,
            task_type=task.task_type.value if isinstance(task.task_type, TaskType) else str(task.task_type),
            source_type=task.source_type.value if isinstance(task.source_type, TaskSourceType) else str(task.source_type),
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
            raise NotFoundException(f"Task not found: {task_id}")
        return self._to_entity(model)

    def list_recent(self, limit: int = 20) -> list[TaskEntity]:
        stmt = select(TaskModel).order_by(TaskModel.created_at.desc()).limit(limit)
        return [self._to_entity(item) for item in self.db.execute(stmt).scalars().all()]

    def update_status(
        self,
        task_id: str,
        status: TaskStatus | str,
        current_step: str,
        progress: int | None = None,
        error_message: str | None = None,
    ) -> TaskEntity:
        model = self.db.get(TaskModel, task_id)
        if not model:
            raise NotFoundException(f"Task not found: {task_id}")
        model.status = status.value if isinstance(status, TaskStatus) else str(status)
        model.current_step = current_step
        if progress is not None:
            model.progress = progress
        self.db.commit()
        self.db.refresh(model)
        return self._to_entity(model)

    def update_plan(self, task_id: str, plan_json: dict) -> TaskEntity:
        model = self.db.get(TaskModel, task_id)
        if not model:
            raise NotFoundException(f"Task not found: {task_id}")
        model.plan_json = plan_json
        self.db.commit()
        self.db.refresh(model)
        return self._to_entity(model)

    def confirm_to_queued(
        self,
        task_id: str,
        confirmed_by: str | None = None,
    ) -> bool:
        """
        原子确认任务。

        只有 WAITING_CONFIRM 状态可以被更新为 QUEUED。
        返回 True 表示当前请求确认成功。
        返回 False 表示任务已经被别人确认、取消或执行。
        """
        stmt = (
            update(TaskModel)
            .where(TaskModel.id == task_id)
            .where(TaskModel.status == TaskStatus.WAITING_CONFIRM.value)
            .values(
                status=TaskStatus.QUEUED.value,
                current_step="任务已确认，等待执行",
                progress=5,
                confirmed_by=confirmed_by,
                confirmed_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            )
        )

        result = self.db.execute(stmt)
        return result.rowcount == 1

    def mark_running_if_queued(self, task_id: str) -> bool:
        """
        worker 领取任务后，将 task 从 QUEUED 改为 RUNNING。
        """
        stmt = (
            update(TaskModel)
            .where(TaskModel.id == task_id)
            .where(TaskModel.status == TaskStatus.QUEUED.value)
            .values(
                status=TaskStatus.RUNNING.value,
                current_step="任务已被 worker 领取，开始执行",
                progress=10,
                updated_at=datetime.utcnow(),
            )
        )

        result = self.db.execute(stmt)
        return result.rowcount == 1

    @staticmethod
    def _to_entity(model: TaskModel) -> TaskEntity:
        return TaskEntity(
            id=model.id,
            title=model.title,
            task_type=TaskType(model.task_type),
            source_type=TaskSourceType(model.source_type),
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
