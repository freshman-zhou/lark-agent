import json

from packages.agent.intent.explicit_intent_schema import ExplicitIntentResult
from packages.agent.llm.openai_llm_client import OpenAILLMClient
from packages.shared.config import get_settings
from packages.shared.logger import get_logger


logger = get_logger(__name__)


class ExplicitIntentDetector:
    """LLM intent router for explicit @Agent messages.

    This layer only decides the user's intent and normalizes the command. It
    does not plan execution steps; TaskPreviewAgent/Planner still does that.
    """

    SYSTEM_PROMPT = """你是 Agent-Pilot 的显式@消息意图识别器。
用户已经 @ 了机器人。请判断用户是否要求 Agent 创建或推进一个可执行办公任务。

你只做意图识别和命令归一化，不要拆执行步骤。

可选 intent：
- CREATE_TASK：用户明确希望 Agent 生成/整理/总结/沉淀/输出某种工作产物。
- QUERY_PROGRESS：用户询问某个任务进度。
- MODIFY_TASK：用户想修改已有任务或输出。
- CHAT：普通问答、闲聊、询问信息，但没有要求创建任务。
- UNKNOWN：无法判断。

可选 task_type：
- CREATE_DOC_FROM_IM
- GENERATE_SLIDES
- IM_TO_DOC_TO_PPT
- SUMMARIZE_DISCUSSION
- UNKNOWN

只有当用户真的要求产生文档、PPT、摘要、方案、报告、会议纪要、汇报材料等交付物时，才返回 CREATE_TASK。
如果用户意图像任务但信息不足，请 requires_clarification=true 并给出澄清问题。

请严格输出 JSON，不要输出额外解释。"""

    def __init__(self):
        self.settings = get_settings()
        self.llm_client = OpenAILLMClient()

    async def detect(
        self,
        text: str,
        context_messages: list[dict] | None = None,
    ) -> ExplicitIntentResult:
        if not self.settings.explicit_intent_enable_llm:
            return ExplicitIntentResult(
                intent="UNKNOWN",
                confidence=0,
                reason="explicit intent LLM disabled",
            )

        payload = {
            "message": text,
            "recent_chat_context": context_messages or [],
            "output_schema": {
                "intent": "CREATE_TASK | QUERY_PROGRESS | MODIFY_TASK | CHAT | UNKNOWN",
                "confidence": 0.0,
                "task_type": "IM_TO_DOC_TO_PPT | CREATE_DOC_FROM_IM | GENERATE_SLIDES | SUMMARIZE_DISCUSSION | UNKNOWN",
                "normalized_command": "归一化后的任务指令",
                "title": "短标题",
                "deliverables": ["交付物"],
                "requires_clarification": False,
                "clarifying_questions": ["澄清问题"],
                "reason": "判断依据",
            },
        }

        raw = await self.llm_client.chat_json(
            system_prompt=self.SYSTEM_PROMPT,
            user_prompt=json.dumps(payload, ensure_ascii=False),
        )

        result = ExplicitIntentResult.from_dict(raw)

        logger.info(
            "Explicit intent detected: intent=%s confidence=%s task_type=%s",
            result.intent,
            result.confidence,
            result.task_type,
        )

        return result
