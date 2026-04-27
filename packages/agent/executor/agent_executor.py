from dataclasses import dataclass


@dataclass
class AgentNextAction:
    action_name: str
    skill_name: str
    params: dict
    finish: bool = False


class AgentExecutor:
    """第一版模拟 AgentExecutor。

    后续这里会替换成 LLM：
    LLM 根据 goal、preview、memory、history_actions、skills 决定下一步 action。
    """

    def decide_next_action(
        self,
        preview: dict,
        executed_skill_names: list[str],
    ) -> AgentNextAction:
        task_type = preview.get("task_type")

        if task_type == "CREATE_DOC_FROM_IM":
            sequence = [
                "feishu.collect_chat_context",
                "discussion.summarize",
                "doc.generate",
                "delivery.prepare_result",
            ]
        elif task_type == "GENERATE_SLIDES":
            sequence = [
                "feishu.collect_chat_context",
                "discussion.summarize",
                "slide.generate",
                "delivery.prepare_result",
            ]
        elif task_type == "SUMMARIZE_DISCUSSION":
            sequence = [
                "feishu.collect_chat_context",
                "discussion.summarize",
                "delivery.prepare_result",
            ]
        else:
            sequence = [
                "feishu.collect_chat_context",
                "discussion.summarize",
                "doc.generate",
                "slide.generate",
                "delivery.prepare_result",
            ]

        for skill_name in sequence:
            if skill_name not in executed_skill_names:
                return AgentNextAction(
                    action_name=self._skill_to_action_name(skill_name),
                    skill_name=skill_name,
                    params={},
                    finish=False,
                )

        return AgentNextAction(
            action_name="finish",
            skill_name="",
            params={},
            finish=True,
        )

    @staticmethod
    def _skill_to_action_name(skill_name: str) -> str:
        return skill_name.replace(".", "_")