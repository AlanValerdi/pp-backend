import logging

from app.core.config import get_settings


def configure_logging() -> None:
    level = get_settings().log_level.upper()
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
