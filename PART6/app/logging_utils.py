import json
import logging
from datetime import datetime, timezone


def configure_logging(level: str) -> logging.Logger:
    logging.basicConfig(level=getattr(logging, level.upper(), logging.INFO), format="%(message)s")
    return logging.getLogger("part6-agent")


def log_event(logger: logging.Logger, event: str, **fields) -> None:
    payload = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "event": event,
        **fields,
    }
    logger.info(json.dumps(payload, ensure_ascii=True))
