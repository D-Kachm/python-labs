import logging
from pathlib import Path


def configure_logging(
    level: str,
    path: Path,
    console: bool = True,
) -> logging.Logger:
    path.parent.mkdir(parents=True, exist_ok=True)
    numeric_level = getattr(logging, level.upper(), logging.INFO)
    handlers: list[logging.Handler] = [
        logging.FileHandler(path, encoding="utf-8"),
    ]
    if console:
        handlers.append(logging.StreamHandler())
    logging.basicConfig(
        level=numeric_level,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        handlers=handlers,
        force=True,
    )
    return logging.getLogger("car_catalog")
