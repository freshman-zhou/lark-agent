from packages.agent.skills.base_skill import BaseSkill, SkillResult


class SlideGenerateSkill(BaseSkill):
    name = "slide.generate"
    description = "根据 discussion_summary 和 doc_markdown 生成 PPT 结构。后续接入 PPT 渲染服务。"

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

        return SkillResult(
            success=True,
            message="已基于真实讨论总结生成 PPT 结构，暂未创建在线演示稿",
            data={
                "slide_json": slide_json,
            },
        )
