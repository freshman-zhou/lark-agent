from packages.agent.skills.base_skill import BaseSkill, SkillResult


class SlideDeckAutoConfirmSkill(BaseSkill):
    name = "slide.confirm_deck"
    description = "预留完整 PPT 确认节点；当前自动确认。"

    async def run(self, params: dict, context) -> SkillResult:
        slide_json = context.memory.get("slide_json") or {}
        if not slide_json:
            return SkillResult(success=False, error="slide_json is empty")

        context.memory["slide_deck_status"] = "CONFIRMED"
        context.memory["slide_deck_confirm_mode"] = "AUTO"
        context.memory["slide_deck_confirmed"] = True

        return SkillResult(
            success=True,
            message="完整 PPT 已自动确认",
            data={
                "slide_deck_status": "CONFIRMED",
                "slide_deck_confirm_mode": "AUTO",
                "slide_deck_confirmed": True,
            },
        )
