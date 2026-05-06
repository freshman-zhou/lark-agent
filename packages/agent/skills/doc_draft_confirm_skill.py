from packages.agent.skills.base_skill import BaseSkill, SkillResult
from packages.domain.artifact import ArtifactStatus
from packages.domain.task.task_status import TaskStatus
from packages.infrastructure.db.repositories.artifact_repository import ArtifactRepository
from packages.infrastructure.db.repositories.task_repository import TaskRepository

from langgraph.types import interrupt


class DocDraftConfirmSkill(BaseSkill):
    name = "doc.confirm_draft"
    description = "文档草稿人工确认节点；未定稿时中断 LangGraph，等待工作台确认。"

    async def run(self, params: dict, context) -> SkillResult:
        artifact = ArtifactRepository(context.db).get_by_task_and_type(
            context.task.id,
            "doc_draft",
        )

        if artifact.status != ArtifactStatus.APPROVED.value:
            TaskRepository(context.db).update_status(
                task_id=context.task.id,
                status=TaskStatus.WAITING_USER_INPUT,
                current_step="等待用户确认：文档草稿",
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
                    "message": "等待用户在工作台定稿：文档草稿",
                    "workbench_url": f"/workbench/?task_id={context.task.id}",
                }
            )

        markdown = (artifact.content_json or {}).get("markdown") or ""
        if not markdown:
            return SkillResult(
                success=False,
                error="approved doc_draft artifact has empty markdown",
            )

        context.memory["doc_markdown"] = markdown
        context.memory["doc_draft_status"] = "CONFIRMED"
        context.memory["doc_draft_confirm_mode"] = "USER"
        context.memory["doc_draft_confirmed"] = True

        return SkillResult(
            success=True,
            message="文档草稿已由用户确认",
            data={
                "doc_markdown": markdown,
                "doc_draft_status": "CONFIRMED",
                "doc_draft_confirm_mode": "USER",
                "doc_draft_confirmed": True,
                "artifact_id": artifact.id,
                "artifact_revision": artifact.revision,
            },
        )
