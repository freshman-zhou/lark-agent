import uuid
from datetime import datetime

from sqlalchemy import select, func
from sqlalchemy.orm import Session

from packages.domain.task.task_status import AgentActionStatus
from packages.infrastructure.db.models.agent_action_model import AgentActionModel


class AgentActionRepository:
    def __init__(self, db: Session):
        self.db = db

    def next_sequence(self, task_id: str) -> int:
        stmt = select(func.max(AgentActionModel.sequence)).where(
            AgentActionModel.task_id == task_id
        )
        current = self.db.scalar(stmt)
        return int(current or 0) + 1

    def create_running(
        self,
        task_id: str,
        action_name: str,
        skill_name: str,
        input_json: dict | None = None,
    ) -> AgentActionModel:
        action = AgentActionModel(
            id=f"action_{uuid.uuid4().hex[:12]}",
            task_id=task_id,
            sequence=self.next_sequence(task_id),
            action_name=action_name,
            skill_name=skill_name,
            status=AgentActionStatus.RUNNING.value,
            input_json=input_json,
            output_json=None,
            error_message=None,
            started_at=datetime.utcnow(),
            finished_at=None,
        )

        self.db.add(action)
        self.db.commit()
        self.db.refresh(action)

        return action

    def mark_success(
        self,
        action_id: str,
        output_json: dict | None = None,
    ) -> AgentActionModel:
        action = self.get_by_id(action_id)

        action.status = AgentActionStatus.SUCCESS.value
        action.output_json = output_json
        action.finished_at = datetime.utcnow()

        self.db.commit()
        self.db.refresh(action)

        return action

    def mark_failed(
        self,
        action_id: str,
        error_message: str,
        output_json: dict | None = None,
    ) -> AgentActionModel:
        action = self.get_by_id(action_id)

        action.status = AgentActionStatus.FAILED.value
        action.error_message = error_message
        action.output_json = output_json
        action.finished_at = datetime.utcnow()

        self.db.commit()
        self.db.refresh(action)

        return action

    def get_by_id(self, action_id: str) -> AgentActionModel:
        stmt = select(AgentActionModel).where(AgentActionModel.id == action_id)
        action = self.db.scalar(stmt)

        if action is None:
            raise ValueError(f"Agent action not found: {action_id}")

        return action

    def list_by_task(self, task_id: str) -> list[AgentActionModel]:
        stmt = (
            select(AgentActionModel)
            .where(AgentActionModel.task_id == task_id)
            .order_by(AgentActionModel.sequence.asc())
        )
        return list(self.db.execute(stmt).scalars().all())