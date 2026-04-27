from packages.agent.skills.base_skill import BaseSkill, SkillResult


class FeishuCollectContextSkill(BaseSkill):
    name = "feishu.collect_chat_context"
    description = "收集飞书群聊上下文。第一版先返回模拟消息，后续接入飞书历史消息 API。"

    async def run(self, params: dict, context) -> SkillResult:
        mock_messages = [
            "我们需要一个能从群聊自动生成方案文档的工具。",
            "最好还能根据文档生成汇报 PPT。",
            "要支持用户确认后再执行，避免 Agent 误操作。",
        ]

        context.memory["chat_messages"] = mock_messages

        return SkillResult(
            success=True,
            message="已收集群聊上下文",
            data={
                "messages": mock_messages,
                "count": len(mock_messages),
            },
        )