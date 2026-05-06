from packages.agent.skills.base_skill import BaseSkill, SkillResult
from packages.agent.skills.artifact_review_helper import ArtifactReviewHelper


class DocOutlineAutoConfirmSkill(BaseSkill):
    name = "doc.confirm_outline"
    description = "文档大纲人工确认节点；未定稿时中断 LangGraph，等待工作台确认。"

    def __init__(self):
        self.review_helper = ArtifactReviewHelper(
            artifact_type="doc_outline",
            memory_key="doc_outline",
            display_name="文档大纲",
        )

    async def run(self, params: dict, context) -> SkillResult:
        outline = context.memory.get("doc_outline") or {}

        if not outline:
            return SkillResult(
                success=False,
                error="doc_outline is empty, please run doc.plan_outline first",
            )

        review_result = self.review_helper.confirm_or_interrupt(context)

        context.memory["doc_outline_status"] = "CONFIRMED"
        context.memory["doc_outline_confirm_mode"] = "USER"
        context.memory["doc_outline_confirmed"] = True

        return SkillResult(
            success=True,
            message="文档大纲已由用户确认",
            data={
                "doc_outline": review_result["doc_outline"],
                "doc_outline_status": "CONFIRMED",
                "doc_outline_confirm_mode": "USER",
                "doc_outline_confirmed": True,
                "artifact_id": review_result["artifact_id"],
                "artifact_revision": review_result["artifact_revision"],
            },
        )
