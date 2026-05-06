from packages.agent.skills.base_skill import BaseSkill, SkillResult


class SlideOutlineAutoConfirmSkill(BaseSkill):
    name = "slide.confirm_outline"
    description = "预留 PPT 大纲确认节点；当前自动确认。"

    async def run(self, params: dict, context) -> SkillResult:
        outline = context.memory.get("slide_outline") or {}
        if not outline:
            return SkillResult(success=False, error="slide_outline is empty")

        context.memory["slide_outline_status"] = "CONFIRMED"
        context.memory["slide_outline_confirm_mode"] = "AUTO"
        context.memory["slide_outline_confirmed"] = True

        return SkillResult(
            success=True,
            message="PPT 大纲已自动确认",
            data={
                "slide_outline": outline,
                "slide_outline_status": "CONFIRMED",
                "slide_outline_confirm_mode": "AUTO",
                "slide_outline_confirmed": True,
            },
        )
