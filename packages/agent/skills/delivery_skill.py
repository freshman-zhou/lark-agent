from packages.agent.skills.base_skill import BaseSkill, SkillResult


class DeliverySkill(BaseSkill):
    name = "delivery.prepare_result"
    description = "整理最终交付结果。"

    async def run(self, params: dict, context) -> SkillResult:
        result = {
            "summary": "任务已完成，已整理交付结果。",
        }

        doc_url = context.memory.get("doc_url")
        slide_url = context.memory.get("slide_url")
        document_id = context.memory.get("document_id")
        presentation_id = context.memory.get("presentation_id")

        if doc_url:
            result["doc_url"] = doc_url

        if document_id:
            result["document_id"] = document_id

        if slide_url:
            result["slide_url"] = slide_url

        if presentation_id:
            result["presentation_id"] = presentation_id

        context.memory["delivery_result"] = result

        return SkillResult(
            success=True,
            message="已准备交付结果",
            data=result,
        )
