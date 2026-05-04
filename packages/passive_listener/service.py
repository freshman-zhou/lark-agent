from dataclasses import dataclass
from typing import Any

from sqlalchemy.orm import Session

from packages.application.message_triage_service import MessageTriageResult
from packages.integrations.feishu.event.feishu_event_dto import FeishuMessageEventDTO
from packages.passive_listener.detector import PassiveTaskDetector
from packages.passive_listener.models import ListenerChatMessageModel
from packages.passive_listener.notify_service import PassiveSuggestionNotifyService
from packages.passive_listener.repository import (
    ListenerDetectionStatus,
    PassiveListenerRepository,
)
from packages.passive_listener.signal import PassiveSignalScorer
from packages.shared.config import get_settings
from packages.shared.logger import get_logger


logger = get_logger(__name__)


@dataclass
class DetectionPlan:
    should_run: bool
    reason: str
    chat_id: str
    context_hash: str | None = None
    signal_score: int = 0
    messages: list[ListenerChatMessageModel] | None = None


class PassiveListenerService:
    def __init__(self, db: Session):
        self.db = db
        self.settings = get_settings()
        self.repository = PassiveListenerRepository(db)
        self.signal_scorer = PassiveSignalScorer()
        self.detector = PassiveTaskDetector()
        self.notify_service = PassiveSuggestionNotifyService(self.repository)

    def capture_message(
        self,
        *,
        event: FeishuMessageEventDTO,
        triage: MessageTriageResult | None = None,
    ) -> dict[str, Any]:
        if not self.settings.passive_listener_enabled:
            return {
                "captured": False,
                "reason": "passive listener disabled",
            }

        if event.is_mention_bot:
            return {
                "captured": False,
                "reason": "explicit bot mention is handled by main workflow",
            }

        if (event.message_type or "").lower() not in {"text", "post"}:
            return {
                "captured": False,
                "reason": f"unsupported message type: {event.message_type}",
            }

        text = (event.content or "").strip()
        if len(text) < 4:
            return {
                "captured": False,
                "reason": "message too short",
            }

        signal_score = self.signal_scorer.score(text)
        is_candidate = self.signal_scorer.is_candidate(text)

        model, created = self.repository.create_chat_message(
            event=event,
            triage_intent=triage.intent.value if triage else None,
            triage_reason=triage.reason if triage else None,
            signal_score=signal_score,
            is_candidate=is_candidate,
        )

        logger.info(
            "Passive listener captured message: chat_id=%s message_id=%s "
            "created=%s score=%s candidate=%s",
            event.chat_id,
            event.message_id,
            created,
            signal_score,
            is_candidate,
        )

        return {
            "captured": True,
            "created": created,
            "message_id": model.message_id,
            "signal_score": signal_score,
            "is_candidate": is_candidate,
        }

    def build_detection_plan(self, chat_id: str) -> DetectionPlan:
        messages = self.repository.list_recent_messages(
            chat_id=chat_id,
            window_minutes=self.settings.passive_listener_window_minutes,
            limit=self.settings.passive_listener_max_context_messages,
        )

        if not messages:
            return DetectionPlan(
                should_run=False,
                reason="no recent messages",
                chat_id=chat_id,
            )

        signal_score = sum(message.signal_score or 0 for message in messages)
        has_strong_trigger = self.signal_scorer.has_strong_trigger(
            [message.content for message in messages[-3:]]
        )

        enough_window = (
            len(messages) >= self.settings.passive_listener_min_messages
            and signal_score >= self.settings.passive_listener_min_signal_score
        )

        if not enough_window and not has_strong_trigger:
            return DetectionPlan(
                should_run=False,
                reason=(
                    "insufficient context: "
                    f"messages={len(messages)}, signal_score={signal_score}"
                ),
                chat_id=chat_id,
                signal_score=signal_score,
                messages=messages,
            )

        if self.repository.has_recent_detection(
            chat_id=chat_id,
            cooldown_minutes=self.settings.passive_listener_llm_cooldown_minutes,
        ):
            return DetectionPlan(
                should_run=False,
                reason="detection cooldown active",
                chat_id=chat_id,
                signal_score=signal_score,
                messages=messages,
            )

        if self.repository.has_recent_suggestion(
            chat_id=chat_id,
            cooldown_minutes=self.settings.passive_listener_suggestion_cooldown_minutes,
        ):
            return DetectionPlan(
                should_run=False,
                reason="suggestion cooldown active",
                chat_id=chat_id,
                signal_score=signal_score,
                messages=messages,
            )

        context_hash = self.repository.build_context_hash(messages)

        if self.repository.get_detection_by_context_hash(context_hash):
            return DetectionPlan(
                should_run=False,
                reason="context already detected",
                chat_id=chat_id,
                context_hash=context_hash,
                signal_score=signal_score,
                messages=messages,
            )

        if self.repository.get_suggestion_by_context_hash(context_hash):
            return DetectionPlan(
                should_run=False,
                reason="context already suggested",
                chat_id=chat_id,
                context_hash=context_hash,
                signal_score=signal_score,
                messages=messages,
            )

        reason = "strong trigger phrase" if has_strong_trigger else "score threshold"

        return DetectionPlan(
            should_run=True,
            reason=reason,
            chat_id=chat_id,
            context_hash=context_hash,
            signal_score=signal_score,
            messages=messages,
        )

    async def run_detection_for_chat(self, chat_id: str) -> dict[str, Any]:
        plan = self.build_detection_plan(chat_id)

        if not plan.should_run:
            return {
                "ran": False,
                "chat_id": chat_id,
                "reason": plan.reason,
            }

        messages = plan.messages or []
        source_message_ids = [message.message_id for message in messages]
        llm_input_json = self.detector.build_llm_input_json(
            chat_id=chat_id,
            messages=messages,
            signal_score=plan.signal_score,
        )

        detection_run, created = self.repository.create_detection_run(
            chat_id=chat_id,
            context_hash=plan.context_hash or "",
            message_count=len(messages),
            signal_score=plan.signal_score,
            trigger_reason=plan.reason,
            source_message_ids=source_message_ids,
            llm_input_json=llm_input_json,
        )

        if not created:
            return {
                "ran": False,
                "chat_id": chat_id,
                "reason": "detection already exists",
                "detection_id": detection_run.id,
            }

        try:
            result = await self.detector.detect(
                chat_id=chat_id,
                messages=messages,
                signal_score=plan.signal_score,
            )

            if self._should_create_suggestion(result):
                suggestion, suggestion_created = self.repository.create_suggestion(
                    chat_id=chat_id,
                    context_hash=plan.context_hash or "",
                    task_type=result.task_type,
                    task_title=result.task_title,
                    suggested_command=result.suggested_command,
                    confidence=result.confidence,
                    reason=result.reason,
                    missing_info=result.missing_info,
                    suggested_deliverables=result.suggested_deliverables,
                    source_message_ids=result.evidence_message_ids
                    or source_message_ids,
                )
                status = ListenerDetectionStatus.DETECTED
                card_sent = await self._send_suggestion_card_if_needed(
                    suggestion=suggestion,
                    suggestion_created=suggestion_created,
                )
            else:
                suggestion = None
                suggestion_created = False
                card_sent = False
                status = ListenerDetectionStatus.NOT_DETECTED

            self.repository.finish_detection_run(
                detection_id=detection_run.id,
                status=status,
                llm_output_json=result.raw,
            )
            self.repository.mark_messages_consumed(source_message_ids)

            return {
                "ran": True,
                "chat_id": chat_id,
                "detection_id": detection_run.id,
                "status": status,
                "suggestion_id": suggestion.id if suggestion else None,
                "suggestion_created": suggestion_created,
                "suggestion_card_sent": card_sent,
                "confidence": result.confidence,
            }

        except Exception as exc:
            logger.exception(
                "Passive listener detection failed: chat_id=%s detection_id=%s",
                chat_id,
                detection_run.id,
            )
            self.repository.finish_detection_run(
                detection_id=detection_run.id,
                status=ListenerDetectionStatus.FAILED,
                error_message=str(exc),
            )

            return {
                "ran": True,
                "chat_id": chat_id,
                "detection_id": detection_run.id,
                "status": ListenerDetectionStatus.FAILED,
                "error": str(exc),
            }

    async def run_once(self) -> dict[str, Any]:
        chat_ids = self.repository.list_active_chat_ids(
            window_minutes=self.settings.passive_listener_window_minutes
        )

        results = []
        for chat_id in chat_ids:
            results.append(await self.run_detection_for_chat(chat_id))

        return {
            "chat_count": len(chat_ids),
            "results": results,
        }

    def _should_create_suggestion(self, result) -> bool:
        return (
            result.should_suggest_task
            and result.confidence >= self.settings.passive_listener_confidence_threshold
            and result.task_type != "UNKNOWN"
            and bool(result.task_title)
            and bool(result.suggested_command)
        )

    async def _send_suggestion_card_if_needed(
        self,
        *,
        suggestion,
        suggestion_created: bool,
    ) -> bool:
        if not suggestion_created:
            return False

        try:
            response = await self.notify_service.send_suggestion_card(suggestion)
            return response is not None
        except Exception:
            logger.exception(
                "Failed to send passive suggestion card: suggestion_id=%s",
                suggestion.id,
            )
            return False
