from packages.agent.nodes.intent_router_node import IntentRouterNode
from packages.agent.schemas.plan_schema import PlanResult, PlanStep
from packages.domain.task.task_status import TaskType


class PlannerNode:
    """第一版规则 Planner。

    当前先不用 LLM，保证主链路稳定。
    后续接入 LLM 后，可以保留它作为 fallback。
    """

    def __init__(self):
        self.intent_router = IntentRouterNode()

    def plan(self, command: str) -> PlanResult:
        task_type = self.intent_router.route(command)

        if task_type == TaskType.IM_TO_DOC_TO_PPT:
            return PlanResult(
                task_type=task_type.value,
                title=self._make_title(command, "整理讨论并生成汇报材料"),
                need_confirm=True,
                steps=[
                    PlanStep(
                        name="collect_context",
                        description="收集飞书群聊上下文",
                        tool="feishu_im",
                        need_confirm=False,
                    ),
                    PlanStep(
                        name="summarize_discussion",
                        description="总结讨论内容，提取需求、结论和待确认问题",
                        tool="discussion_summary_agent",
                        need_confirm=False,
                    ),
                    PlanStep(
                        name="generate_doc",
                        description="生成方案文档",
                        tool="doc_agent",
                        need_confirm=True,
                    ),
                    PlanStep(
                        name="generate_slides",
                        description="根据方案文档生成汇报 PPT",
                        tool="slide_agent",
                        need_confirm=True,
                    ),
                    PlanStep(
                        name="deliver_result",
                        description="将文档和 PPT 链接发送回飞书群",
                        tool="feishu_message",
                        need_confirm=False,
                    ),
                ],
            )

        if task_type == TaskType.CREATE_DOC_FROM_IM:
            return PlanResult(
                task_type=task_type.value,
                title=self._make_title(command, "整理讨论并生成方案文档"),
                need_confirm=True,
                steps=[
                    PlanStep(
                        name="collect_context",
                        description="收集飞书群聊上下文",
                        tool="feishu_im",
                    ),
                    PlanStep(
                        name="summarize_discussion",
                        description="总结群聊中的需求、结论和待办事项",
                        tool="discussion_summary_agent",
                    ),
                    PlanStep(
                        name="generate_doc",
                        description="生成方案文档",
                        tool="doc_agent",
                        need_confirm=True,
                    ),
                    PlanStep(
                        name="deliver_result",
                        description="发送文档链接到飞书群",
                        tool="feishu_message",
                    ),
                ],
            )

        if task_type == TaskType.GENERATE_SLIDES:
            return PlanResult(
                task_type=task_type.value,
                title=self._make_title(command, "生成汇报 PPT"),
                need_confirm=True,
                steps=[
                    PlanStep(
                        name="collect_material",
                        description="收集已有文档或群聊材料",
                        tool="feishu_im",
                    ),
                    PlanStep(
                        name="generate_slide_outline",
                        description="生成 PPT 大纲",
                        tool="slide_agent",
                        need_confirm=True,
                    ),
                    PlanStep(
                        name="generate_slides",
                        description="生成 PPT 页面内容",
                        tool="slide_agent",
                    ),
                    PlanStep(
                        name="deliver_result",
                        description="发送 PPT 结果到飞书群",
                        tool="feishu_message",
                    ),
                ],
            )

        if task_type == TaskType.SUMMARIZE_DISCUSSION:
            return PlanResult(
                task_type=task_type.value,
                title=self._make_title(command, "总结群聊讨论"),
                need_confirm=False,
                steps=[
                    PlanStep(
                        name="collect_context",
                        description="收集最近群聊消息",
                        tool="feishu_im",
                    ),
                    PlanStep(
                        name="summarize_discussion",
                        description="生成讨论摘要",
                        tool="discussion_summary_agent",
                    ),
                    PlanStep(
                        name="send_summary",
                        description="将摘要发送回飞书群",
                        tool="feishu_message",
                    ),
                ],
            )

        return PlanResult(
            task_type=TaskType.UNKNOWN.value,
            title=self._make_title(command, "未识别任务"),
            need_confirm=True,
            steps=[
                PlanStep(
                    name="clarify_intent",
                    description="向用户澄清任务目标",
                    tool="feishu_message",
                    need_confirm=True,
                )
            ],
        )

    @staticmethod
    def _make_title(command: str, fallback: str) -> str:
        text = (command or "").strip()
        if not text:
            return fallback

        text = text.replace("\n", " ").strip()
        return text[:60]