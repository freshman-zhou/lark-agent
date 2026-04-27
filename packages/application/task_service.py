import re
import uuid
from datetime import datetime

from sqlalchemy.orm import Session

from packages.agent.planner.task_preview_agent import TaskPreviewAgent
from packages.domain.task.task_status import TaskSourceType, TaskStatus
from packages.infrastructure.db.models.task_model import TaskModel
from packages.infrastructure.db.repositories.task_repository import TaskRepository
from packages.shared.exceptions import TaskNotFoundException


class TaskService:
    def __init__(self, db: Session):
        self.db = db
        self.repository = TaskRepository(db)
        self.preview_agent = TaskPreviewAgent()

    #根据用户信息生成任务预览。当前v1简单生成一个任务
    def create_preview_from_feishu_message(
        self,
        content: str,
        chat_id: str,
        message_id: str,
        creator_id: str,
    ) -> TaskModel:
        command = self._clean_command(content)

        preview = self.preview_agent.generate_preview(command)

        task = TaskModel(
            id=self._generate_task_id(),
            title=preview["title"],
            task_type=preview["task_type"],
            status=TaskStatus.WAITING_CONFIRM.value,
            source_type=TaskSourceType.FEISHU_IM.value,
            source_chat_id=chat_id,
            source_message_id=message_id,
            creator_id=creator_id,
            progress=0,
            current_step="已生成任务预览，等待用户确认",
            plan_json=preview,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )

        return self.repository.create(task)

    def create_from_feishu_message(
        self,
        content: str,
        chat_id: str,
        message_id: str,
        creator_id: str,
    ) -> TaskModel:
        """兼容旧代码。

        后续统一使用 create_preview_from_feishu_message。
        """
        return self.create_preview_from_feishu_message(
            content=content,
            chat_id=chat_id,
            message_id=message_id,
            creator_id=creator_id,
        )

    def get_task(self, task_id: str) -> TaskModel:
        task = self.repository.get_by_id(task_id)
        if task is None:
            raise TaskNotFoundException(task_id)
        return task

    def list_recent_tasks(self, limit: int = 20) -> list[TaskModel]:
        return self.repository.list_recent(limit)

    @staticmethod
    def _generate_task_id() -> str:
        return f"task_{uuid.uuid4().hex[:12]}"

    @staticmethod
    def _clean_command(content: str) -> str:
        text = content or ""

        text = re.sub(r"<at[^>]*>.*?</at>", "", text)
        text = re.sub(r"@\S+", "", text)

        text = text.replace("\u2005", " ")
        text = re.sub(r"\s+", " ", text)

        return text.strip()
