from packages.agent.skills.base_skill import BaseSkill, SkillResult
from packages.agent.skills.artifact_review_helper import ArtifactReviewHelper


class SlideOutlineAutoConfirmSkill(BaseSkill):
    name = "slide.confirm_outline"
    description = "PPT 大纲人工确认节点；未定稿时中断 LangGraph，等待工作台确认。"

    def __init__(self):
        self.review_helper = ArtifactReviewHelper(
            artifact_type="slide_outline",
            memory_key="slide_outline",
            display_name="PPT 大纲",
        )

    async def run(self, params: dict, context) -> SkillResult:
        outline = context.memory.get("slide_outline") or {}
        if not outline:
            return SkillResult(success=False, error="slide_outline is empty")

        review_result = self.review_helper.confirm_or_interrupt(context)

        context.memory["slide_outline_status"] = "CONFIRMED"
        context.memory["slide_outline_confirm_mode"] = "USER"
        context.memory["slide_outline_confirmed"] = True

        return SkillResult(
            success=True,
            message="PPT 大纲已由用户确认",
            data={
                "slide_outline": review_result["slide_outline"],
                "slide_outline_status": "CONFIRMED",
                "slide_outline_confirm_mode": "USER",
                "slide_outline_confirmed": True,
                "artifact_id": review_result["artifact_id"],
                "artifact_revision": review_result["artifact_revision"],
            },
        )
