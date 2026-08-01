"""Personal Wiki - Main entry point."""
from __future__ import annotations

import argparse
import asyncio

from bot.handlers import main as run_bot
from web.app import app as web_app


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
        import uvicorn
        uvicorn.run(web_app, host="0.0.0.0", port=8000)
    elif args.mode == "all":
        # Run both in separate threads
        import threading
        web_thread = threading.Thread(
            target=lambda: asyncio.run(run_bot()),
            daemon=True,
        )
        web_thread.start()
        import uvicorn
        uvicorn.run(web_app, host="0.0.0.0", port=8000)


if __name__ == "__main__":
    main()
