from packages.agent.skills.base_skill import BaseSkill, SkillResult
from packages.domain.artifact import ArtifactStatus
from packages.infrastructure.db.repositories.artifact_repository import ArtifactRepository
from packages.integrations.feishu.slides.slides_cli_api import FeishuSlidesCliApi
from packages.shared.exceptions import AppException


class SlideCreatePresentationSkill(BaseSkill):
    name = "slide.create_presentation"
    description = "根据已确认 slide_json 创建飞书演示稿。"

    def __init__(self):
        self.slides_api = FeishuSlidesCliApi()

    async def run(self, params: dict, context) -> SkillResult:
        slide_json = self._get_approved_slide_json(context)
        if not slide_json:
            return SkillResult(success=False, error="slide_json is empty")

        try:
            presentation = await self.slides_api.create_presentation(
                title=slide_json.get("title") or context.task.title,
                slide_json=slide_json,
            )
        except AppException as exc:
            return SkillResult(success=False, message="创建飞书演示稿失败", error=exc.message, data={"detail": exc.detail, "slide_json": slide_json})
        except Exception as exc:
            return SkillResult(success=False, message="创建飞书演示稿失败", error=str(exc), data={"slide_json": slide_json})

        context.memory["presentation_id"] = presentation.presentation_id
        context.memory["slide_url"] = presentation.url
        context.memory["slides_create_result"] = presentation.raw or {}

        return SkillResult(
            success=True,
            message="已创建飞书演示稿",
            data={
                "presentation_id": presentation.presentation_id,
                "slide_url": presentation.url,
                "slides_create_result": presentation.raw or {},
            },
        )

    @staticmethod
    def _get_approved_slide_json(context) -> dict:
        try:
            artifact = ArtifactRepository(context.db).get_by_task_and_type(
                context.task.id,
                "slide_deck",
            )
            if artifact.status == ArtifactStatus.APPROVED.value:
                return artifact.content_json or {}
        except Exception:
            pass

        return context.memory.get("slide_json") or {}
