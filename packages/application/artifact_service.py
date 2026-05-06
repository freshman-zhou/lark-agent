from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from packages.domain.artifact import ArtifactType
from packages.infrastructure.db.models.artifact_model import ArtifactModel
from packages.infrastructure.db.repositories.artifact_repository import ArtifactRepository
from packages.infrastructure.db.repositories.task_job_repository import TaskJobRepository
from packages.infrastructure.db.repositories.task_repository import TaskRepository
from packages.domain.task.task_status import TaskStatus


class ArtifactService:
    """
    协同产物服务。

    Agent 生成大纲/草稿后保存为 artifact；飞书内工作台对 artifact 做多人多端编辑、
    定稿或要求重新生成。
    """

    _SKILL_ARTIFACT_MAP = {
        "doc.plan_outline": (ArtifactType.DOC_OUTLINE.value, "doc_outline"),
        "doc.generate": (ArtifactType.DOC_DRAFT.value, "doc_markdown"),
        "slide.plan_outline": (ArtifactType.SLIDE_OUTLINE.value, "slide_outline"),
        "slide.generate_deck": (ArtifactType.SLIDE_DECK.value, "slide_json"),
    }

    def __init__(self, db: Session):
        self.db = db
        self.repository = ArtifactRepository(db)
        self.task_repository = TaskRepository(db)
        self.task_job_repository = TaskJobRepository(db)

    def capture_skill_output(
        self,
        *,
        task_id: str,
        skill_name: str,
        action_id: str | None,
        output_json: dict[str, Any] | None,
    ) -> ArtifactModel | None:
        mapping = self._SKILL_ARTIFACT_MAP.get(skill_name)
        if mapping is None:
            return None

        data = (output_json or {}).get("data") or {}
        if not isinstance(data, dict):
            return None

        artifact_type, data_key = mapping
        raw_content = data.get(data_key)
        if raw_content in (None, "", {}, []):
            return None

        task = self.task_repository.get_model_by_id(task_id)
        content_json = self._normalize_content_json(
            artifact_type=artifact_type,
            raw_content=raw_content,
            data=data,
            fallback_title=task.title,
        )
        title = self._infer_title(
            artifact_type=artifact_type,
            content_json=content_json,
            fallback_title=task.title,
        )

        return self.repository.create_or_replace_generated(
            task_id=task_id,
            artifact_type=artifact_type,
            title=title,
            content_json=content_json,
            source_action_id=action_id,
        )

    def list_by_task(self, task_id: str) -> list[dict[str, Any]]:
        self.task_repository.get_by_id(task_id)
        return [self.serialize(item, include_content=False) for item in self.repository.list_by_task(task_id)]

    def get(self, artifact_id: str) -> dict[str, Any]:
        return self.serialize(self.repository.get_by_id(artifact_id), include_content=True)

    def update_content(
        self,
        *,
        artifact_id: str,
        base_revision: int,
        content_json: dict[str, Any],
        title: str | None = None,
        edited_by: str | None = None,
    ) -> dict[str, Any]:
        artifact = self.repository.update_content(
            artifact_id=artifact_id,
            base_revision=base_revision,
            content_json=content_json,
            title=title,
            edited_by=edited_by,
        )
        return self.serialize(artifact, include_content=True)

    def approve(
        self,
        *,
        artifact_id: str,
        reviewed_by: str | None = None,
        feedback_text: str | None = None,
    ) -> dict[str, Any]:
        artifact = self.repository.approve(
            artifact_id=artifact_id,
            reviewed_by=reviewed_by,
            feedback_text=feedback_text,
        )
        self._resume_waiting_task_if_needed(artifact.task_id)
        return self.serialize(artifact, include_content=True)

    async def request_regenerate(
        self,
        *,
        artifact_id: str,
        requested_by: str | None = None,
        feedback_text: str | None = None,
    ) -> dict[str, Any]:
        artifact = self.repository.request_regenerate(
            artifact_id=artifact_id,
            requested_by=requested_by,
            feedback_text=feedback_text,
        )

        from packages.application.artifact_regeneration_service import (
            ArtifactRegenerationService,
        )

        regenerated = await ArtifactRegenerationService(self.db).regenerate(artifact)
        return self.serialize(regenerated, include_content=True)

    @classmethod
    def _normalize_content_json(
        cls,
        *,
        artifact_type: str,
        raw_content: Any,
        data: dict[str, Any],
        fallback_title: str,
    ) -> dict[str, Any]:
        if artifact_type == ArtifactType.DOC_DRAFT.value:
            return {
                "title": fallback_title,
                "format": "markdown",
                "markdown": str(raw_content),
                "doc_outline": data.get("doc_outline") or {},
                "research_context": data.get("research_context") or {},
            }

        if isinstance(raw_content, dict):
            return raw_content

        return {
            "title": fallback_title,
            "value": raw_content,
        }

    @staticmethod
    def _infer_title(
        *,
        artifact_type: str,
        content_json: dict[str, Any],
        fallback_title: str,
    ) -> str:
        title = str(content_json.get("title") or fallback_title or artifact_type).strip()
        return title[:255] or artifact_type

    @staticmethod
    def serialize(
        artifact: ArtifactModel,
        *,
        include_content: bool,
    ) -> dict[str, Any]:
        item = {
            "id": artifact.id,
            "task_id": artifact.task_id,
            "artifact_type": artifact.artifact_type,
            "title": artifact.title,
            "status": artifact.status,
            "revision": artifact.revision,
            "source_action_id": artifact.source_action_id,
            "last_edited_by": artifact.last_edited_by,
            "reviewed_by": artifact.reviewed_by,
            "reviewed_at": ArtifactService._dt(artifact.reviewed_at),
            "feedback_text": artifact.feedback_text,
            "created_at": ArtifactService._dt(artifact.created_at),
            "updated_at": ArtifactService._dt(artifact.updated_at),
        }

        if include_content:
            item["content_json"] = artifact.content_json

        return item

    @staticmethod
    def _dt(value: datetime | None) -> str | None:
        return value.isoformat() if value else None

    def _resume_waiting_task_if_needed(self, task_id: str) -> None:
        try:
            task = self.task_repository.get_by_id(task_id)
            if task.status != TaskStatus.WAITING_USER_INPUT:
                return

            resumed_job = self.task_job_repository.resume_waiting_by_task(task_id)
            if resumed_job is None:
                return

            self.task_repository.update_status(
                task_id=task_id,
                status=TaskStatus.QUEUED,
                current_step="用户已定稿，等待继续执行",
                progress=task.progress,
            )
        except Exception:
            self.db.rollback()
            raise
