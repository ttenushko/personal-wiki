"""Personal Wiki - Main entry point."""
from __future__ import annotations

import argparse
import asyncio

from wikillm.bot.handlers import main as run_bot
from wikillm.config.settings import settings
from wikillm.core.logger import logger
from wikillm.web.app import app as web_app


def _run_web() -> None:
    import uvicorn

    uvicorn.run(web_app, host=settings.web_host, port=settings.web_port)


def main() -> None:
    parser = argparse.ArgumentParser(description="Personal Wiki")
    parser.add_argument(
        "mode",
        choices=["bot", "web", "all"],
        help="Run mode: bot, web, or all",
    )
    args = parser.parse_args()

    if args.mode == "bot":
        asyncio.run(run_bot())
    elif args.mode == "web":
        _run_web()
    elif args.mode == "all":
        import threading

        bot_thread = threading.Thread(
            target=lambda: asyncio.run(run_bot()),
            daemon=True,
            name="wiki-bot",
        )
        bot_thread.start()
        try:
            _run_web()
        except KeyboardInterrupt:
            logger.info("Остановлено пользователем.")
        finally:
            logger.info("Завершение работы.")


if __name__ == "__main__":
    main()
