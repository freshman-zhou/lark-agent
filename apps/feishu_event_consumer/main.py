import lark_oapi as lark
from packages.shared.fix_ssl import *
from apps.feishu_event_consumer.handlers.message_event_handler import (
    handle_p2_im_message_receive_v1,
)
from apps.feishu_event_consumer.handlers.card_action_handler import (
    handle_p2_card_action_trigger,
)
from packages.application.task_worker_service import task_worker_service
from packages.infrastructure.db.database import init_db
from packages.shared.config import get_settings
from packages.shared.logger import get_logger

logger = get_logger(__name__)


def build_event_handler() -> lark.EventDispatcherHandler:
    settings = get_settings()
    print("Registering Feishu message handler:", handle_p2_im_message_receive_v1, flush=True)

    return (
        lark.EventDispatcherHandler.builder(
            settings.feishu_encrypt_key or "",
            settings.feishu_verification_token or "",
            lark.LogLevel.DEBUG if settings.debug else lark.LogLevel.INFO,
        )
        .register_p2_im_message_receive_v1(handle_p2_im_message_receive_v1)
        .register_p2_card_action_trigger(handle_p2_card_action_trigger)
        .build()
    )


def main() -> None:
    settings = get_settings()
    init_db()
    task_worker_service.start_background()

    if not settings.feishu_app_id or not settings.feishu_app_secret:
        raise RuntimeError("FEISHU_APP_ID and FEISHU_APP_SECRET must be configured")

    event_handler = build_event_handler()
    
    print("正在连接飞书服务器...")

    client = lark.ws.Client(
        settings.feishu_app_id,
        settings.feishu_app_secret,
        event_handler=event_handler,
        log_level=lark.LogLevel.DEBUG if settings.debug else lark.LogLevel.INFO,
    )

    logger.info("Starting Feishu long-connection event consumer...")
    try:
        client.start()
    finally:
        task_worker_service.stop()


if __name__ == "__main__":
    main()
