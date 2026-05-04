import asyncio

from packages.infrastructure.db.database import SessionLocal, init_db
from packages.passive_listener.service import PassiveListenerService
from packages.shared.config import get_settings
from packages.shared.logger import get_logger


logger = get_logger(__name__)


async def run_forever() -> None:
    settings = get_settings()

    logger.info(
        "Passive listener worker started: interval=%s enable_llm=%s",
        settings.passive_listener_poll_interval_seconds,
        settings.passive_listener_enable_llm,
    )

    while True:
        db = SessionLocal()

        try:
            service = PassiveListenerService(db)
            result = await service.run_once()

            logger.info(
                "Passive listener worker tick: chat_count=%s results=%s",
                result.get("chat_count"),
                result.get("results"),
            )

        except Exception as exc:
            logger.exception("Passive listener worker tick failed: %s", exc)

        finally:
            db.close()

        await asyncio.sleep(settings.passive_listener_poll_interval_seconds)


def main() -> None:
    init_db()
    asyncio.run(run_forever())


if __name__ == "__main__":
    main()
