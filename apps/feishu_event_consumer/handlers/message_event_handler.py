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


async def handle_p2_im_message_receive_v1(data: lark.im.v1.P2ImMessageReceiveV1) -> None:
    """飞书长连接接收消息事件处理器。

    当前 MVP 里直接创建 task 并回复。
    后续接入 LLM、文档、PPT 后，这里应只入队，然后立即返回，耗时工作交给 worker。
    """
    db = SessionLocal()

    try:
        event = normalizer.normalize(data)
        if event is None:
            logger.info("Ignored unsupported long-connection event")
            return

        service = FeishuEventService(db)
        await service.handle_message_event(event)

    except Exception as exc:
        logger.error("Failed to handle Feishu long-connection event: %s", exc)
        logger.debug("Traceback:\n%s", traceback.format_exc())

    finally:
        db.close()