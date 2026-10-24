import cProfile
import os
import pstats
from statistics import mean
import time
import tracemalloc
from typing import Any, Callable

def run_cprofile(func: Callable[..., Any], *args: Any, **kwargs: Any) -> pstats.Stats:
    profiler = cProfile.Profile()
    profiler.enable()
    func(*args, **kwargs)
    profiler.disable()
    return pstats.Stats(profiler)

def measure_memory_and_peak(
    func: Callable[..., Any], *args: Any, **kwargs: Any
) -> tuple[Any, float, float]:
    tracemalloc.start()
    result = func(*args, **kwargs)
    current, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    return result, current / 1024.0, peak / 1024.0

def benchmark(
    name: str, func: Callable[..., Any], *args: Any, **kwargs: Any
) -> tuple[str, float, Any]:
    start = time.perf_counter()
    result = func(*args, **kwargs)
    elapsed = time.perf_counter() - start
    return name, elapsed, result

def benchmark_repeated(
    func: Callable[..., Any], *args: Any, repeats: int = 5, **kwargs: Any
) -> float:
    times: list[float] = []
    for _ in range(repeats):
        start = time.perf_counter()
        func(*args, **kwargs)
        elapsed = time.perf_counter() - start
        times.append(elapsed)
    return mean(times) if times else 0.0

def calculate_speedup(baseline_time: float, optimized_time: float) -> float:
    if optimized_time <= 0.0:
        return 0.0
    return baseline_time / optimized_time

def get_system_cpu_count() -> int:
    return os.cpu_count() or 1
