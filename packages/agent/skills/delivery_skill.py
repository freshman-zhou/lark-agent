from packages.agent.skills.base_skill import BaseSkill, SkillResult


class DeliverySkill(BaseSkill):
    name = "delivery.prepare_result"
    description = "整理最终交付结果。"

    async def run(self, params: dict, context) -> SkillResult:
        result = {
            "doc_url": context.memory.get("doc_url", "mock://feishu-doc-url"),
            "slide_url": context.memory.get("slide_url", "mock://slide-preview-url"),
            "summary": "任务已完成，已生成方案文档草稿和 PPT 结构。",
        }

        context.memory["delivery_result"] = result

        return SkillResult(
            success=True,
            message="已准备交付结果",
            data=result,
        )