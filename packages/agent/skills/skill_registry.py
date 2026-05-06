from packages.agent.skills.base_skill import BaseSkill, SkillResult
from packages.agent.skills.delivery_skill import DeliverySkill
from packages.agent.skills.discussion_summary_skill import DiscussionSummarySkill
from packages.agent.skills.doc_draft_confirm_skill import DocDraftConfirmSkill
from packages.agent.skills.doc_generate_skill import DocGenerateSkill
from packages.agent.skills.doc_outline_auto_confirm_skill import DocOutlineAutoConfirmSkill
from packages.agent.skills.doc_outline_plan_skill import DocOutlinePlanSkill
from packages.agent.skills.doc_publish_skill import DocPublishSkill
from packages.agent.skills.doc_research_plan_skill import DocResearchPlanSkill
from packages.agent.skills.feishu_collect_context_skill import FeishuCollectContextSkill
from packages.agent.skills.image_search_collect_skill import ImageSearchCollectSkill
from packages.agent.skills.research_collect_skill import ResearchCollectSkill
from packages.agent.skills.slide_create_presentation_skill import SlideCreatePresentationSkill
from packages.agent.skills.slide_deck_auto_confirm_skill import SlideDeckAutoConfirmSkill
from packages.agent.skills.slide_generate_skill import SlideGenerateSkill
from packages.agent.skills.slide_image_plan_skill import SlideImagePlanSkill
from packages.agent.skills.slide_outline_auto_confirm_skill import SlideOutlineAutoConfirmSkill
from packages.agent.skills.slide_outline_plan_skill import SlideOutlinePlanSkill
from packages.agent.skills.slide_research_collect_skill import SlideResearchCollectSkill
from packages.agent.skills.slide_research_plan_skill import SlideResearchPlanSkill


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
        self.register(DocDraftConfirmSkill())
        self.register(DocPublishSkill())
        self.register(SlideOutlinePlanSkill())
        self.register(SlideOutlineAutoConfirmSkill())
        self.register(SlideResearchPlanSkill())
        self.register(SlideResearchCollectSkill())
        self.register(SlideImagePlanSkill())
        self.register(ImageSearchCollectSkill())
        self.register(SlideGenerateSkill())
        self.register(SlideDeckAutoConfirmSkill())
        self.register(SlideCreatePresentationSkill())
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
