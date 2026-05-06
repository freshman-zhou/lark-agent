from packages.agent.skills.base_skill import BaseSkill, SkillResult
from packages.agent.skills.artifact_review_helper import ArtifactReviewHelper


class SlideDeckAutoConfirmSkill(BaseSkill):
    name = "slide.confirm_deck"
    description = "完整 PPT 人工确认节点；未定稿时中断 LangGraph，等待工作台确认。"

    def __init__(self):
        self.review_helper = ArtifactReviewHelper(
            artifact_type="slide_deck",
            memory_key="slide_json",
            display_name="完整 PPT",
        )

    async def run(self, params: dict, context) -> SkillResult:
        slide_json = context.memory.get("slide_json") or {}
        if not slide_json:
            return SkillResult(success=False, error="slide_json is empty")

        review_result = self.review_helper.confirm_or_interrupt(context)

        context.memory["slide_deck_status"] = "CONFIRMED"
        context.memory["slide_deck_confirm_mode"] = "USER"
        context.memory["slide_deck_confirmed"] = True
        context.memory["slide_json"] = review_result["slide_json"]

        return SkillResult(
            success=True,
            message="完整 PPT 已由用户确认",
            data={
                "slide_json": review_result["slide_json"],
                "slide_deck_status": "CONFIRMED",
                "slide_deck_confirm_mode": "USER",
                "slide_deck_confirmed": True,
                "artifact_id": review_result["artifact_id"],
                "artifact_revision": review_result["artifact_revision"],
            },
        )
