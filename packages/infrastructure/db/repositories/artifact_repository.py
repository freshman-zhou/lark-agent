import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from packages.domain.artifact import ArtifactStatus
from packages.infrastructure.db.models.artifact_model import ArtifactModel
from packages.shared.exceptions import ConflictException, NotFoundException


class ArtifactRepository:
    def __init__(self, db: Session):
        self.db = db

    def create_or_replace_generated(
        self,
        *,
        task_id: str,
        artifact_type: str,
        title: str,
        content_json: dict[str, Any],
        source_action_id: str | None = None,
    ) -> ArtifactModel:
        artifact = self.get_by_task_and_type(task_id, artifact_type, raise_if_missing=False)
        now = datetime.utcnow()

        if artifact is None:
            artifact = ArtifactModel(
                id=f"artifact_{uuid.uuid4().hex[:12]}",
                task_id=task_id,
                artifact_type=artifact_type,
                title=title,
                status=ArtifactStatus.GENERATED.value,
                revision=1,
                content_json=content_json,
                source_action_id=source_action_id,
                created_at=now,
                updated_at=now,
            )
            self.db.add(artifact)
        else:
            artifact.title = title
            artifact.status = ArtifactStatus.GENERATED.value
            artifact.revision = int(artifact.revision or 0) + 1
            artifact.content_json = content_json
            artifact.source_action_id = source_action_id
            artifact.feedback_text = None
            artifact.reviewed_by = None
            artifact.reviewed_at = None
            artifact.updated_at = now

        self.db.commit()
        self.db.refresh(artifact)
        return artifact

    def list_by_task(self, task_id: str) -> list[ArtifactModel]:
        stmt = (
            select(ArtifactModel)
            .where(ArtifactModel.task_id == task_id)
            .order_by(ArtifactModel.updated_at.desc())
        )
        return list(self.db.execute(stmt).scalars().all())

    def get_by_id(self, artifact_id: str) -> ArtifactModel:
        artifact = self.db.get(ArtifactModel, artifact_id)
        if artifact is None:
            raise NotFoundException(f"Artifact not found: {artifact_id}")
        return artifact

    def get_by_task_and_type(
        self,
        task_id: str,
        artifact_type: str,
        *,
        raise_if_missing: bool = True,
    ) -> ArtifactModel | None:
        stmt = (
            select(ArtifactModel)
            .where(ArtifactModel.task_id == task_id)
            .where(ArtifactModel.artifact_type == artifact_type)
        )
        artifact = self.db.scalar(stmt)

        if artifact is None and raise_if_missing:
            raise NotFoundException(
                f"Artifact not found: task_id={task_id}, artifact_type={artifact_type}"
            )

        return artifact

    def update_content(
        self,
        *,
        artifact_id: str,
        base_revision: int,
        content_json: dict[str, Any],
        title: str | None = None,
        edited_by: str | None = None,
    ) -> ArtifactModel:
        artifact = self.get_by_id(artifact_id)

        if int(artifact.revision or 0) != base_revision:
            raise ConflictException(
                message="Artifact revision conflict",
                detail={
                    "artifact_id": artifact_id,
                    "expected_revision": artifact.revision,
                    "base_revision": base_revision,
                },
            )

        artifact.content_json = content_json
        if title:
            artifact.title = title
        artifact.revision = int(artifact.revision or 0) + 1
        artifact.status = ArtifactStatus.EDITING.value
        artifact.last_edited_by = edited_by
        artifact.updated_at = datetime.utcnow()

        self.db.commit()
        self.db.refresh(artifact)
        return artifact

    def approve(
        self,
        *,
        artifact_id: str,
        reviewed_by: str | None = None,
        feedback_text: str | None = None,
    ) -> ArtifactModel:
        artifact = self.get_by_id(artifact_id)
        artifact.status = ArtifactStatus.APPROVED.value
        artifact.reviewed_by = reviewed_by
        artifact.reviewed_at = datetime.utcnow()
        artifact.feedback_text = feedback_text
        artifact.updated_at = datetime.utcnow()

        self.db.commit()
        self.db.refresh(artifact)
        return artifact

    def request_regenerate(
        self,
        *,
        artifact_id: str,
        requested_by: str | None = None,
        feedback_text: str | None = None,
    ) -> ArtifactModel:
        artifact = self.get_by_id(artifact_id)
        artifact.status = ArtifactStatus.REGENERATE_REQUESTED.value
        artifact.reviewed_by = requested_by
        artifact.reviewed_at = datetime.utcnow()
        artifact.feedback_text = feedback_text
        artifact.updated_at = datetime.utcnow()

        self.db.commit()
        self.db.refresh(artifact)
        return artifact

    def mark_regenerating(self, artifact_id: str) -> ArtifactModel:
        artifact = self.get_by_id(artifact_id)
        artifact.status = ArtifactStatus.REGENERATING.value
        artifact.updated_at = datetime.utcnow()

        self.db.commit()
        self.db.refresh(artifact)
        return artifact
