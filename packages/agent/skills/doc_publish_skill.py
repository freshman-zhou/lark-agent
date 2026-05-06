from packages.agent.skills.base_skill import BaseSkill, SkillResult
from packages.domain.artifact import ArtifactStatus
from packages.infrastructure.db.repositories.artifact_repository import ArtifactRepository
from packages.integrations.feishu.doc.document_cli_api import FeishuDocumentCliApi
from packages.shared.exceptions import AppException


class DocPublishSkill(BaseSkill):
    name = "doc.publish_document"
    description = "使用已定稿文档草稿创建飞书云文档。"

    def __init__(self):
        self.document_api = FeishuDocumentCliApi()

    async def run(self, params: dict, context) -> SkillResult:
        doc_markdown = self._get_approved_markdown(context)
        if not doc_markdown:
            return SkillResult(success=False, error="doc_markdown is empty")

        try:
            document = await self.document_api.create_document(context.task.title)
            append_result = await self.document_api.append_markdown(
                document=document,
                markdown=doc_markdown,
            )
        except AppException as exc:
            return SkillResult(
                success=False,
                message="创建飞书云文档失败",
                error=exc.message,
                data={
                    "doc_markdown": doc_markdown,
                    "detail": exc.detail,
                },
            )
        except Exception as exc:
            return SkillResult(
                success=False,
                message="创建飞书云文档失败",
                error=str(exc),
                data={
                    "doc_markdown": doc_markdown,
                },
            )

        context.memory["doc_markdown"] = doc_markdown
        context.memory["document_id"] = document.document_id
        context.memory["doc_token"] = document.doc_token
        context.memory["doc_url"] = document.url
        context.memory["doc_create_result"] = document.raw or {}
        context.memory["doc_append_result"] = append_result

        return SkillResult(
            success=True,
            message="已使用定稿内容创建飞书方案文档",
            data={
                "doc_markdown": doc_markdown,
                "document_id": document.document_id,
                "doc_token": document.doc_token,
                "doc_url": document.url,
                "doc_create_result": document.raw or {},
                "doc_append_result": append_result,
            },
        )

    @staticmethod
    def _get_approved_markdown(context) -> str:
        try:
            artifact = ArtifactRepository(context.db).get_by_task_and_type(
                context.task.id,
                "doc_draft",
            )
            if artifact.status == ArtifactStatus.APPROVED.value:
                return (artifact.content_json or {}).get("markdown") or ""
        except Exception:
            pass

        return context.memory.get("doc_markdown") or ""
