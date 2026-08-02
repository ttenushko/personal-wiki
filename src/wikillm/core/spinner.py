from __future__ import annotations

import asyncio
import contextlib
import sys

FRAMES = ["|", "/", "-", "\\"]


class Spinner:
    """A tiny async spinner for the console."""

    def __init__(self, message: str = "") -> None:
        self._message = message
        self._task: asyncio.Task | None = None
        self._frame = 0

    async def _run(self) -> None:
        while True:
            frame = FRAMES[self._frame % len(FRAMES)]
            sys.stdout.write(f"\r{frame} {self._message}")
            sys.stdout.flush()
            self._frame += 1
            await asyncio.sleep(0.1)

    async def start(self) -> None:
        self._task = asyncio.create_task(self._run())

    async def stop(self) -> None:
        if self._task:
            self._task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._task
            sys.stdout.write("\r" + " " * (len(self._message) + 2) + "\r")
            sys.stdout.flush()
            self._task = None


@contextlib.asynccontextmanager
async def spinner(message: str = ""):
    """Run an async block with a spinner in the console."""
    s = Spinner(message)
    await s.start()
    try:
        yield
    finally:
        await s.stop()
