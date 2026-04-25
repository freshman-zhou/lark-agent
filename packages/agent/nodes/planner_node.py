from packages.agent.schemas.plan_schema import PlanStep, TaskPlan


class PlannerNode:
    """第一版假 Planner：用规则生成稳定计划。"""

    def plan(self, task_type: str, user_text: str) -> TaskPlan:
        if task_type == "IM_TO_DOC_TO_PPT":
            steps = [
                PlanStep(id="collect_context", name="收集群聊上下文", module="im_context"),
                PlanStep(id="generate_doc_outline", name="生成文档大纲", module="doc_agent", need_confirm=True),
                PlanStep(id="create_doc", name="创建方案文档", module="feishu_doc"),
                PlanStep(id="generate_slides", name="生成演示稿", module="slide_agent", need_confirm=True),
                PlanStep(id="deliver", name="发送交付结果", module="delivery"),
            ]
        elif task_type == "CREATE_DOC_FROM_IM":
            steps = [
                PlanStep(id="collect_context", name="收集群聊上下文", module="im_context"),
                PlanStep(id="generate_doc_outline", name="生成文档大纲", module="doc_agent", need_confirm=True),
                PlanStep(id="create_doc", name="创建方案文档", module="feishu_doc"),
                PlanStep(id="deliver", name="发送文档链接", module="delivery"),
            ]
        elif task_type == "GENERATE_SLIDES":
            steps = [
                PlanStep(id="collect_material", name="收集文档或群聊材料", module="material_collector"),
                PlanStep(id="generate_slide_outline", name="生成演示稿大纲", module="slide_agent", need_confirm=True),
                PlanStep(id="render_slides", name="渲染演示稿", module="slide_renderer"),
                PlanStep(id="deliver", name="发送演示稿链接", module="delivery"),
            ]
        else:
            steps = [PlanStep(id="reply", name="生成普通助手回复", module="assistant")]

        return TaskPlan(task_type=task_type, summary=f"根据指令生成任务计划：{user_text}", steps=steps)