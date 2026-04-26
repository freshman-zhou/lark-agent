import asyncio
import traceback

import lark_oapi as lark

from packages.application.feishu_event_service import FeishuEventService
from packages.infrastructure.db.database import SessionLocal
from packages.integrations.feishu.event.long_connection_event_normalizer import (
    LongConnectionEventNormalizer,
)
from packages.shared.logger import get_logger

logger = get_logger(__name__)
normalizer = LongConnectionEventNormalizer()

def handle_p2_im_message_receive_v1(data: lark.im.v1.P2ImMessageReceiveV1) -> None:
    print(">>> ENTER handle_p2_im_message_receive_v1", flush=True)
    logger.info("Received Feishu long-connection message event")
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        asyncio.run(_handle_p2_im_message_receive_v1(data))
        return

    task = loop.create_task(_handle_p2_im_message_receive_v1(data))
    task.add_done_callback(_log_unhandled_task_exception)


def _log_unhandled_task_exception(task: asyncio.Task) -> None:
    try:
        task.result()
    except Exception as exc:
        logger.error("Unhandled Feishu event task error: %s", exc)
        logger.debug("Traceback:\n%s", traceback.format_exc())

async def _handle_p2_im_message_receive_v1(data: lark.im.v1.P2ImMessageReceiveV1) -> None:
    """飞书长连接接收消息事件处理器。

    当前 MVP 里直接创建 task 并回复。
    后续接入 LLM、文档、PPT 后，这里应只入队，然后立即返回，耗时工作交给 worker。
    """
    db = SessionLocal()

    try:
        event = normalizer.normalize(data)
        if event is None:
            print(">>> Feishu event normalized to None", flush=True)
            logger.info("Ignored unsupported long-connection event")
            return
        print(f">>> NORMALIZED content={event.content!r}", flush=True)
        logger.info(
            "Normalized Feishu event: chat_id=%s message_id=%s content=%s",
            event.chat_id,
            event.message_id,
            event.content,
        )

        service = FeishuEventService(db)
        await service.handle_message_event(event)

    except Exception as exc:
        logger.error("Failed to handle Feishu long-connection event: %s", exc)
        logger.debug("Traceback:\n%s", traceback.format_exc())

    finally:
        db.close()
