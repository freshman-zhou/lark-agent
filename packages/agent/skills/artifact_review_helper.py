from typing import Any

from langgraph.types import interrupt

from packages.domain.artifact import ArtifactStatus
from packages.domain.task.task_status import TaskStatus
from packages.infrastructure.db.repositories.artifact_repository import ArtifactRepository
from packages.infrastructure.db.repositories.task_repository import TaskRepository


class ArtifactReviewHelper:
    def __init__(self, *, artifact_type: str, memory_key: str, display_name: str):
        self.artifact_type = artifact_type
        self.memory_key = memory_key
        self.display_name = display_name

    def confirm_or_interrupt(self, context) -> dict[str, Any]:
        repository = ArtifactRepository(context.db)
        artifact = repository.get_by_task_and_type(
            context.task.id,
            self.artifact_type,
        )

        if artifact.status == ArtifactStatus.APPROVED.value:
            context.memory[self.memory_key] = artifact.content_json
            return {
                "artifact_id": artifact.id,
                "artifact_type": artifact.artifact_type,
                "artifact_status": artifact.status,
                "artifact_revision": artifact.revision,
                self.memory_key: artifact.content_json,
                "confirm_mode": "USER",
                "confirmed": True,
            }

        TaskRepository(context.db).update_status(
            task_id=context.task.id,
            status=TaskStatus.WAITING_USER_INPUT,
            current_step=f"等待用户确认：{self.display_name}",
            progress=context.task.progress,
        )

        interrupt(
            {
                "type": "artifact_review",
                "task_id": context.task.id,
                "artifact_id": artifact.id,
                "artifact_type": artifact.artifact_type,
                "artifact_status": artifact.status,
                "artifact_revision": artifact.revision,
                "title": artifact.title,
                "message": f"等待用户在工作台定稿：{self.display_name}",
                "workbench_url": f"/workbench/?task_id={context.task.id}",
            }
        )

        refreshed = repository.get_by_id(artifact.id)
        if refreshed.status != ArtifactStatus.APPROVED.value:
            TaskRepository(context.db).update_status(
                task_id=context.task.id,
                status=TaskStatus.WAITING_USER_INPUT,
                current_step=f"等待用户确认：{self.display_name}",
                progress=context.task.progress,
            )
            interrupt(
                {
                    "type": "artifact_review",
                    "task_id": context.task.id,
                    "artifact_id": refreshed.id,
                    "artifact_type": refreshed.artifact_type,
                    "artifact_status": refreshed.status,
                    "artifact_revision": refreshed.revision,
                    "title": refreshed.title,
                    "message": f"产物尚未定稿：{self.display_name}",
                    "workbench_url": f"/workbench/?task_id={context.task.id}",
                }
            )

        context.memory[self.memory_key] = refreshed.content_json
        return {
            "artifact_id": refreshed.id,
            "artifact_type": refreshed.artifact_type,
            "artifact_status": refreshed.status,
            "artifact_revision": refreshed.revision,
            self.memory_key: refreshed.content_json,
            "confirm_mode": "USER",
            "confirmed": True,
        }
