import asyncio
import threading
import traceback

from lark_oapi.event.callback.model.p2_card_action_trigger import (
    P2CardActionTrigger,
    P2CardActionTriggerResponse,
)

from packages.application.card_action_service import CardActionService
from packages.infrastructure.db.database import SessionLocal
from packages.integrations.feishu.event.card_action_normalizer import CardActionNormalizer
from packages.shared.logger import get_logger

logger = get_logger(__name__)
normalizer = CardActionNormalizer()

#处理卡片回传交互
def handle_p2_card_action_trigger(
    data: P2CardActionTrigger,
) -> P2CardActionTriggerResponse:
    """飞书新版卡片回传交互 card.action.trigger。"""

    db = SessionLocal()

    try:
        dto = normalizer.normalize(data)

        service = CardActionService(db)
        result = _run_async_from_sync(service.handle_card_action(dto))

        toast_type = "success" if result.get("ok") else "warning"
        content = result.get("message") or "操作已处理"

        return P2CardActionTriggerResponse(
            {
                "toast": {
                    "type": toast_type,
                    "content": content,
                }
            }
        )

    except Exception as exc:
        logger.error("Failed to handle Feishu card action: %s", exc)
        logger.debug("Traceback:\n%s", traceback.format_exc())

        return P2CardActionTriggerResponse(
            {
                "toast": {
                    "type": "error",
                    "content": f"操作失败：{exc}",
                }
            }
        )

    finally:
        db.close()

#处理异步转同步
def _run_async_from_sync(coro):
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coro)

    result = None
    error = None

    def runner():
        nonlocal result, error
        try:
            result = asyncio.run(coro)
        except Exception as exc:
            error = exc

    thread = threading.Thread(target=runner)
    thread.start()
    thread.join()

    if error is not None:
        raise error

    return result
