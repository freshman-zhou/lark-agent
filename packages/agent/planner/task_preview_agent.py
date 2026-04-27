from typing import Any

from packages.agent.nodes.planner_node import PlannerNode


class TaskPreviewAgent:
    """任务预览 Agent。

    当前第一版内部复用规则 Planner。
    后续接入 LLM 后，只需要替换 generate_preview 内部逻辑。
    """

    def __init__(self):
        self.planner = PlannerNode()

    def generate_preview(self, command: str) -> dict[str, Any]:
        plan = self.planner.plan(command)

        deliverables = self._infer_deliverables(plan.task_type)
        required_resources = self._infer_required_resources(plan.task_type)

        return {
            "title": plan.title,
            "task_type": plan.task_type,
            "goal": plan.title,
            "need_confirm": plan.need_confirm,
            "deliverables": deliverables,
            "required_resources": required_resources,
            "execution_preview": [
                {
                    "name": step.name,
                    "description": step.description,
                    "tool": step.tool,
                    "need_confirm": step.need_confirm,
                }
                for step in plan.steps
            ],
            "clarifying_questions": self._infer_clarifying_questions(plan.task_type),
            "raw_plan": plan.model_dump(),
        }

    @staticmethod
    def _infer_deliverables(task_type: str) -> list[str]:
        if task_type == "IM_TO_DOC_TO_PPT":
            return ["飞书方案文档", "汇报 PPT", "任务执行摘要"]

        if task_type == "CREATE_DOC_FROM_IM":
            return ["飞书方案文档", "讨论摘要"]

        if task_type == "GENERATE_SLIDES":
            return ["汇报 PPT", "演讲备注"]

        if task_type == "SUMMARIZE_DISCUSSION":
            return ["群聊讨论摘要"]

        return ["待确认的任务结果"]

    @staticmethod
    def _infer_required_resources(task_type: str) -> list[str]:
        resources = ["当前用户指令"]

        if task_type in {"IM_TO_DOC_TO_PPT", "CREATE_DOC_FROM_IM", "SUMMARIZE_DISCUSSION"}:
            resources.append("最近一段飞书群聊上下文")

        return resources

    @staticmethod
    def _infer_clarifying_questions(task_type: str) -> list[str]:
        if task_type == "IM_TO_DOC_TO_PPT":
            return [
                "PPT 默认面向项目汇报场景，是否需要指定汇报对象？",
                "PPT 页数默认控制在 6～8 页，是否需要调整？",
            ]

        if task_type == "GENERATE_SLIDES":
            return [
                "是否需要指定 PPT 页数？",
                "是否需要指定汇报对象？",
            ]

        return []