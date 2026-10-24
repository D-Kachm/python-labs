from collections.abc import Sequence
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor
from pathlib import Path
from threading import Lock
from car_catalog.analytics import calculate_efficiency_score

class ThreadSafeCounter:
    def __init__(self, initial_value: int = 0) -> None:
        self._value = initial_value
        self._lock = Lock()

    def increment(self, step: int = 1) -> None:
        with self._lock:
            self._value += step

    @property
    def value(self) -> int:
        with self._lock:
            return self._value

    def reset(self) -> None:
        with self._lock:
            self._value = 0

class UnsafeCounter:
    def __init__(self, initial_value: int = 0) -> None:
        self.value = initial_value

    def increment(self, step: int = 1) -> None:
        current = self.value
        self.value = current + step

def calculate_scores_threads(values: Sequence[float], workers: int = 4) -> list[float]:
    with ThreadPoolExecutor(max_workers=workers) as executor:
        return list(executor.map(calculate_efficiency_score, values))

def calculate_scores_processes(
    values: Sequence[float],
    workers: int = 4,
    chunksize: int = 100,
) -> list[float]:
    with ProcessPoolExecutor(max_workers=workers) as executor:
        return list(executor.map(calculate_efficiency_score, values, chunksize=chunksize))

def _read_single_file(path: Path) -> str:
    return path.read_text(encoding="utf-8")

def load_files_parallel(paths: Sequence[Path], workers: int = 4) -> list[str]:
    with ThreadPoolExecutor(max_workers=workers) as executor:
        return list(executor.map(_read_single_file, paths))

def load_files_sequential(paths: Sequence[Path]) -> list[str]:
    return [_read_single_file(p) for p in paths]
