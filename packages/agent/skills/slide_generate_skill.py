from packages.agent.skills.base_skill import BaseSkill, SkillResult
from packages.integrations.feishu.slides.slides_cli_api import FeishuSlidesCliApi
from packages.shared.exceptions import AppException


class SlideGenerateSkill(BaseSkill):
    name = "slide.generate"
    description = "根据 discussion_summary 和 doc_markdown 生成 PPT 结构，并创建飞书演示稿。"

    def __init__(self):
        self.slides_api = FeishuSlidesCliApi()

    async def run(self, params: dict, context) -> SkillResult:
        summary = context.memory.get("discussion_summary", {})
        slide_outline = summary.get("suggested_slide_outline", [])

        requirements = summary.get("requirements", [])
        decisions = summary.get("decisions", [])
        open_questions = summary.get("open_questions", [])

        slides = [
            {
                "page": 1,
                "type": "cover",
                "title": context.task.title,
                "subtitle": "基于飞书 IM 讨论自动生成",
            },
            {
                "page": 2,
                "type": "background",
                "title": "讨论背景",
                "bullets": [
                    summary.get("summary", "暂无明确背景")
                ],
            },
            {
                "page": 3,
                "type": "requirements",
                "title": "核心需求",
                "bullets": requirements[:5] or ["暂无明确需求"],
            },
            {
                "page": 4,
                "type": "decisions",
                "title": "已确认结论",
                "bullets": decisions[:5] or ["暂无明确结论"],
            },
            {
                "page": 5,
                "type": "open_questions",
                "title": "待确认问题",
                "bullets": open_questions[:5] or ["暂无待确认问题"],
            },
            {
                "page": 6,
                "type": "plan",
                "title": "后续计划",
                "bullets": slide_outline[:5] or [
                    "完善方案文档",
                    "生成正式汇报材料",
                    "补充演讲备注与答辩问题",
                ],
            },
        ]

        slide_json = {
            "title": context.task.title,
            "source": "feishu_chat_context",
            "slides": slides,
        }

        context.memory["slide_json"] = slide_json

        try:
            presentation = await self.slides_api.create_presentation(
                title=context.task.title,
                slide_json=slide_json,
            )
        except AppException as exc:
            return SkillResult(
                success=False,
                message="PPT 结构已生成，但创建飞书演示稿失败",
                error=exc.message,
                data={
                    "slide_json": slide_json,
                    "detail": exc.detail,
                },
            )
        except Exception as exc:
            return SkillResult(
                success=False,
                message="PPT 结构已生成，但创建飞书演示稿失败",
                error=str(exc),
                data={
                    "slide_json": slide_json,
                },
            )

        context.memory["presentation_id"] = presentation.presentation_id
        context.memory["slide_url"] = presentation.url
        context.memory["slides_create_result"] = presentation.raw or {}

        return SkillResult(
            success=True,
            message="已基于真实讨论总结创建飞书演示稿",
            data={
                "slide_json": slide_json,
                "presentation_id": presentation.presentation_id,
                "slide_url": presentation.url,
                "slides_create_result": presentation.raw or {},
            },
        )
