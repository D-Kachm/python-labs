import logging
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from time import perf_counter
from typing import Any, IO
from car_catalog.exceptions import DataExportError

logger = logging.getLogger(__name__)


@contextmanager
def logged_operation(operation: str) -> Iterator[None]:
    logger.info("%s started", operation)
    start = perf_counter()
    try:
        yield
    except Exception:
        logger.exception("%s failed", operation)
        raise
    else:
        elapsed = perf_counter() - start
        logger.info("%s finished in %.6f s", operation, elapsed)


@contextmanager
def timer(name: str) -> Iterator[dict[str, float]]:
    stats = {"elapsed": 0.0}
    start = perf_counter()
    try:
        yield stats
    finally:
        stats["elapsed"] = perf_counter() - start


@contextmanager
def atomic_file_writer(
    path: Path,
    mode: str = "w",
    encoding: str = "utf-8",
) -> Iterator[IO[Any]]:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    file = temporary.open(mode=mode, encoding=encoding)
    try:
        yield file
        file.flush()
        file.close()
        temporary.replace(path)
    except Exception as error:
        file.close()
        temporary.unlink(missing_ok=True)
        raise DataExportError(f"Cannot export data to {path}") from error
