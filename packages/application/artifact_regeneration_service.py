from typing import Any

from sqlalchemy.orm import Session

from packages.agent.runtime.agent_context import AgentContext
from packages.agent.skills.doc_generate_skill import DocGenerateSkill
from packages.agent.skills.doc_outline_plan_skill import DocOutlinePlanSkill
from packages.agent.skills.slide_generate_skill import SlideGenerateSkill
from packages.agent.skills.slide_outline_plan_skill import SlideOutlinePlanSkill
from packages.domain.artifact import ArtifactStatus, ArtifactType
from packages.domain.task.task_status import AgentActionStatus
from packages.infrastructure.db.models.artifact_model import ArtifactModel
from packages.infrastructure.db.repositories.agent_action_repository import (
    AgentActionRepository,
)
from packages.infrastructure.db.repositories.artifact_repository import (
    ArtifactRepository,
)
from packages.infrastructure.db.repositories.task_repository import TaskRepository
from packages.shared.exceptions import BadRequestException


class ArtifactRegenerationService:
    _SKILL_BY_TYPE = {
        ArtifactType.DOC_OUTLINE.value: (DocOutlinePlanSkill, "doc.plan_outline", "doc_outline", {}),
        ArtifactType.DOC_DRAFT.value: (
            DocGenerateSkill,
            "doc.generate",
            "doc_markdown",
            {"create_document": False},
        ),
        ArtifactType.SLIDE_OUTLINE.value: (
            SlideOutlinePlanSkill,
            "slide.plan_outline",
            "slide_outline",
            {},
        ),
        ArtifactType.SLIDE_DECK.value: (
            SlideGenerateSkill,
            "slide.generate_deck",
            "slide_json",
            {},
        ),
    }

    _MEMORY_KEY_BY_TYPE = {
        ArtifactType.DOC_OUTLINE.value: "doc_outline",
        ArtifactType.DOC_DRAFT.value: "doc_markdown",
        ArtifactType.SLIDE_OUTLINE.value: "slide_outline",
        ArtifactType.SLIDE_DECK.value: "slide_json",
    }

    def __init__(self, db: Session):
        self.db = db
        self.artifact_repository = ArtifactRepository(db)
        self.task_repository = TaskRepository(db)
        self.action_repository = AgentActionRepository(db)

    async def regenerate(self, artifact: ArtifactModel) -> ArtifactModel:
        config = self._SKILL_BY_TYPE.get(artifact.artifact_type)
        if config is None:
            raise BadRequestException(
                message=f"Unsupported artifact type for regeneration: {artifact.artifact_type}",
                detail={"artifact_id": artifact.id, "artifact_type": artifact.artifact_type},
            )

        skill_class, skill_name, data_key, params = config
        task = self.task_repository.get_model_by_id(artifact.task_id)
        memory = self._build_memory(task_id=artifact.task_id)
        memory["regeneration_feedback"] = artifact.feedback_text or ""
        memory[self._MEMORY_KEY_BY_TYPE[artifact.artifact_type]] = (
            self._content_to_memory_value(artifact)
        )

        context = AgentContext(
            db=self.db,
            task=task,
            preview=task.plan_json or {},
            memory=memory,
        )

        action = self.action_repository.create_running(
            task_id=artifact.task_id,
            action_name=f"regenerate_{skill_name.replace('.', '_')}",
            skill_name=f"{skill_name}.regenerate",
            input_json={
                "artifact_id": artifact.id,
                "artifact_type": artifact.artifact_type,
                "feedback_text": artifact.feedback_text,
            },
        )

        try:
            self.artifact_repository.mark_regenerating(artifact.id)
            result = await skill_class().run(params=params, context=context)

            output_json = {
                "message": result.message,
                "data": result.data,
            }

            if not result.success:
                self.action_repository.mark_failed(
                    action_id=action.id,
                    error_message=result.error or "Artifact regeneration failed",
                    output_json=output_json,
                )
                raise BadRequestException(
                    message=result.message or "Artifact regeneration failed",
                    detail={
                        "artifact_id": artifact.id,
                        "error": result.error,
                    },
                )

            data = result.data or {}
            regenerated_content = data.get(data_key)
            if regenerated_content in (None, "", {}, []):
                raise BadRequestException(
                    message="Regeneration skill returned empty content",
                    detail={
                        "artifact_id": artifact.id,
                        "skill_name": skill_name,
                        "data_key": data_key,
                    },
                )

            content_json = self._normalize_content_json(
                artifact=artifact,
                data_key=data_key,
                regenerated_content=regenerated_content,
                data=data,
                fallback_title=task.title,
            )
            title = self._infer_title(content_json, artifact.title)

            updated = self.artifact_repository.create_or_replace_generated(
                task_id=artifact.task_id,
                artifact_type=artifact.artifact_type,
                title=title,
                content_json=content_json,
                source_action_id=action.id,
            )
            self.action_repository.mark_success(
                action_id=action.id,
                output_json={
                    **output_json,
                    "artifact_id": updated.id,
                    "artifact_revision": updated.revision,
                },
            )
            return updated

        except Exception as exc:
            refreshed = self.artifact_repository.get_by_id(artifact.id)
            refreshed.status = ArtifactStatus.REGENERATE_REQUESTED.value
            self.db.commit()

            if action.status == AgentActionStatus.RUNNING.value:
                self.action_repository.mark_failed(
                    action_id=action.id,
                    error_message=str(exc),
                    output_json={"error": str(exc)},
                )
            raise

    def _build_memory(self, *, task_id: str) -> dict[str, Any]:
        memory: dict[str, Any] = {}

        for action in self.action_repository.list_by_task(task_id):
            output_json = action.output_json or {}
            data = output_json.get("data") or {}
            if isinstance(data, dict):
                memory.update(data)

        for artifact in self.artifact_repository.list_by_task(task_id):
            memory_key = self._MEMORY_KEY_BY_TYPE.get(artifact.artifact_type)
            if memory_key:
                memory[memory_key] = self._content_to_memory_value(artifact)

        return memory

    @staticmethod
    def _content_to_memory_value(artifact: ArtifactModel) -> Any:
        if artifact.artifact_type == ArtifactType.DOC_DRAFT.value:
            return (artifact.content_json or {}).get("markdown") or ""

        return artifact.content_json

    @staticmethod
    def _normalize_content_json(
        *,
        artifact: ArtifactModel,
        data_key: str,
        regenerated_content: Any,
        data: dict[str, Any],
        fallback_title: str,
    ) -> dict[str, Any]:
        if artifact.artifact_type == ArtifactType.DOC_DRAFT.value:
            return {
                "title": fallback_title,
                "format": "markdown",
                "markdown": str(regenerated_content),
                "doc_outline": data.get("doc_outline") or {},
                "research_context": data.get("research_context") or {},
            }

        if isinstance(regenerated_content, dict):
            return regenerated_content

        return {
            "title": artifact.title,
            data_key: regenerated_content,
        }

    @staticmethod
    def _infer_title(content_json: dict[str, Any], fallback_title: str) -> str:
        return str(content_json.get("title") or fallback_title)[:255]
