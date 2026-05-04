import json
from dataclasses import dataclass
from typing import Any

from packages.agent.llm.openai_llm_client import OpenAILLMClient
from packages.passive_listener.models import ListenerChatMessageModel
from packages.shared.config import get_settings
from packages.shared.logger import get_logger


logger = get_logger(__name__)


@dataclass
class PassiveDetectionResult:
    should_suggest_task: bool
    confidence: float
    task_type: str
    task_title: str
    suggested_command: str
    reason: str
    evidence_message_ids: list[str]
    missing_info: list[str]
    suggested_deliverables: list[str]
    raw: dict[str, Any]


class PassiveTaskDetector:
    """LLM-backed task opportunity detector.

    The LLM is deliberately behind a feature flag. The passive listener can
    collect and score context safely before suggestions are enabled.
    """

    SYSTEM_PROMPT = """你是 Agent-Pilot 的被动任务发现器。
你的任务是阅读群聊上下文，判断这段讨论是否已经形成一个明确、可执行、值得建议创建的办公任务。

只在满足以下条件时 should_suggest_task=true：
1. 群聊中形成了明确的交付物，例如文档、方案、PPT、汇报材料、会议纪要、总结。
2. 任务可以由 Agent 根据上下文继续推进。
3. 不是普通闲聊、单句想法、没有产物的讨论。

可选 task_type：
- CREATE_DOC_FROM_IM
- GENERATE_SLIDES
- IM_TO_DOC_TO_PPT
- SUMMARIZE_DISCUSSION
- UNKNOWN

请严格输出 JSON，不要输出额外解释。"""

    def __init__(self):
        self.settings = get_settings()
        self.llm_client = OpenAILLMClient()

    async def detect(
        self,
        *,
        chat_id: str,
        messages: list[ListenerChatMessageModel],
        signal_score: int,
    ) -> PassiveDetectionResult:
        if not self.settings.passive_listener_enable_llm:
            return PassiveDetectionResult(
                should_suggest_task=False,
                confidence=0,
                task_type="UNKNOWN",
                task_title="",
                suggested_command="",
                reason="passive listener LLM detection is disabled",
                evidence_message_ids=[],
                missing_info=[],
                suggested_deliverables=[],
                raw={
                    "disabled": True,
                    "chat_id": chat_id,
                    "signal_score": signal_score,
                },
            )

        user_prompt = self._build_user_prompt(
            chat_id=chat_id,
            messages=messages,
            signal_score=signal_score,
        )

        raw = await self.llm_client.chat_json(
            system_prompt=self.SYSTEM_PROMPT,
            user_prompt=user_prompt,
        )

        return self._normalize_result(raw)

    def build_llm_input_json(
        self,
        *,
        chat_id: str,
        messages: list[ListenerChatMessageModel],
        signal_score: int,
    ) -> dict[str, Any]:
        return {
            "chat_id": chat_id,
            "signal_score": signal_score,
            "messages": [
                {
                    "message_id": message.message_id,
                    "sender_id": message.sender_id,
                    "content": message.content,
                    "created_at": message.created_at.isoformat()
                    if message.created_at
                    else None,
                }
                for message in messages
            ],
        }

    def _build_user_prompt(
        self,
        *,
        chat_id: str,
        messages: list[ListenerChatMessageModel],
        signal_score: int,
    ) -> str:
        payload = self.build_llm_input_json(
            chat_id=chat_id,
            messages=messages,
            signal_score=signal_score,
        )

        return (
            "请判断以下群聊上下文是否应建议创建 Agent 任务。\n"
            "输出 JSON schema：\n"
            "{\n"
            '  "should_suggest_task": true,\n'
            '  "confidence": 0.86,\n'
            '  "task_type": "IM_TO_DOC_TO_PPT",\n'
            '  "task_title": "...",\n'
            '  "suggested_command": "...",\n'
            '  "reason": "...",\n'
            '  "evidence_message_ids": ["..."],\n'
            '  "missing_info": ["..."],\n'
            '  "suggested_deliverables": ["..."]\n'
            "}\n\n"
            f"上下文：\n{json.dumps(payload, ensure_ascii=False)}"
        )

    @staticmethod
    def _normalize_result(raw: dict[str, Any]) -> PassiveDetectionResult:
        return PassiveDetectionResult(
            should_suggest_task=bool(raw.get("should_suggest_task")),
            confidence=float(raw.get("confidence") or 0),
            task_type=str(raw.get("task_type") or "UNKNOWN"),
            task_title=str(raw.get("task_title") or ""),
            suggested_command=str(raw.get("suggested_command") or ""),
            reason=str(raw.get("reason") or ""),
            evidence_message_ids=list(raw.get("evidence_message_ids") or []),
            missing_info=list(raw.get("missing_info") or []),
            suggested_deliverables=list(raw.get("suggested_deliverables") or []),
            raw=raw,
        )
