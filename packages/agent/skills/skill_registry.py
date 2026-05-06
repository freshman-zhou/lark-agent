from packages.agent.skills.base_skill import BaseSkill, SkillResult
from packages.agent.skills.delivery_skill import DeliverySkill
from packages.agent.skills.discussion_summary_skill import DiscussionSummarySkill
from packages.agent.skills.doc_generate_skill import DocGenerateSkill
from packages.agent.skills.doc_outline_auto_confirm_skill import DocOutlineAutoConfirmSkill
from packages.agent.skills.doc_outline_plan_skill import DocOutlinePlanSkill
from packages.agent.skills.doc_research_plan_skill import DocResearchPlanSkill
from packages.agent.skills.feishu_collect_context_skill import FeishuCollectContextSkill
from packages.agent.skills.research_collect_skill import ResearchCollectSkill
from packages.agent.skills.slide_generate_skill import SlideGenerateSkill


class SkillRegistry:
    def __init__(self):
        self._skills: dict[str, BaseSkill] = {}

        self.register(FeishuCollectContextSkill())
        self.register(DiscussionSummarySkill())
        self.register(DocOutlinePlanSkill())
        self.register(DocOutlineAutoConfirmSkill())
        self.register(DocResearchPlanSkill())
        self.register(ResearchCollectSkill())
        self.register(DocGenerateSkill())
        self.register(SlideGenerateSkill())
        self.register(DeliverySkill())

    def register(self, skill: BaseSkill) -> None:
        if not skill.name:
            raise ValueError("Skill name is required")
        self._skills[skill.name] = skill

    def list_skills(self) -> list[dict]:
        return [
            {
                "name": skill.name,
                "description": skill.description,
            }
            for skill in self._skills.values()
        ]

    async def execute(
        self,
        skill_name: str,
        params: dict,
        context,
    ) -> SkillResult:
        skill = self._skills.get(skill_name)

        if skill is None:
            return SkillResult(
                success=False,
                error=f"Skill not found: {skill_name}",
            )

        return await skill.run(params=params, context=context)
