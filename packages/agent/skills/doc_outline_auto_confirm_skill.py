from packages.agent.skills.base_skill import BaseSkill, SkillResult


class DocOutlineAutoConfirmSkill(BaseSkill):
    name = "doc.confirm_outline"
    description = "预留大纲确认节点；当前自动确认，后续可替换为卡片或 WebSocket 人工确认。"

    async def run(self, params: dict, context) -> SkillResult:
        outline = context.memory.get("doc_outline") or {}

        if not outline:
            return SkillResult(
                success=False,
                error="doc_outline is empty, please run doc.plan_outline first",
            )

        context.memory["doc_outline_status"] = "CONFIRMED"
        context.memory["doc_outline_confirm_mode"] = "AUTO"
        context.memory["doc_outline_confirmed"] = True

        return SkillResult(
            success=True,
            message="文档大纲已自动确认",
            data={
                "doc_outline": outline,
                "doc_outline_status": "CONFIRMED",
                "doc_outline_confirm_mode": "AUTO",
                "doc_outline_confirmed": True,
            },
        )
