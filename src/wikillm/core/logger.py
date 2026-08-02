import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

# Корень проекта: родительский каталог пакета src/wikillm
PROJECT_ROOT = Path(__file__).resolve().parents[3]
LOG_FILE = PROJECT_ROOT / "wiki.log"

logger = logging.getLogger("wiki")
logger.setLevel(logging.DEBUG)
logger.propagate = False


class _NoTracebackHandler(logging.StreamHandler):
    """Console handler that hides tracebacks (they go to the log file only)."""

    def format(self, record: logging.LogRecord) -> str:
        saved_exc_info = record.exc_info
        saved_exc_text = record.exc_text
        record.exc_info = None
        record.exc_text = None
        try:
            return super().format(record)
        finally:
            record.exc_info = saved_exc_info
            record.exc_text = saved_exc_text


_fh = RotatingFileHandler(
    LOG_FILE,
    maxBytes=1_000_000,
    backupCount=3,
    encoding="utf-8",
)
_fh.setLevel(logging.DEBUG)
_fh.setFormatter(
    logging.Formatter("%(asctime)s %(levelname)s [%(name)s] %(message)s")
)
logger.addHandler(_fh)

_sh = _NoTracebackHandler(sys.stderr)
_sh.setLevel(logging.WARNING)
_sh.setFormatter(logging.Formatter("%(message)s"))
logger.addHandler(_sh)
