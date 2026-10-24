from pathlib import Path
import pstats
from threading import Thread
import pytest
from car_catalog.analytics import (
    cached_brand_statistics,
    calculate_efficiency_score,
    calculate_scores_sequential,
    generate_sample_prices,
    invalidate_brand_statistics_cache,
    statistics_numpy,
    statistics_python,
)
from car_catalog.parallel import (
    ThreadSafeCounter,
    UnsafeCounter,
    calculate_scores_processes,
    calculate_scores_threads,
    load_files_parallel,
    load_files_sequential,
)
from car_catalog.profiling import (
    benchmark,
    benchmark_repeated,
    calculate_speedup,
    get_system_cpu_count,
    measure_memory_and_peak,
    run_cprofile,
)


def test_numpy_statistics_matches_python() -> None:
    values = [25000.0, 32000.0, 48000.0, 15000.0, 89000.0, 42000.0]
    py_res = statistics_python(values)
    np_res = statistics_numpy(values)

    assert np_res["average"] == pytest.approx(py_res["average"], rel=1e-6)
    assert np_res["minimum"] == pytest.approx(py_res["minimum"], rel=1e-6)
    assert np_res["maximum"] == pytest.approx(py_res["maximum"], rel=1e-6)
    assert np_res["std"] == pytest.approx(py_res["std"], rel=1e-6)


def test_statistics_empty_list() -> None:
    py_res = statistics_python([])
    np_res = statistics_numpy([])
    assert py_res == {"average": 0.0, "minimum": 0.0, "maximum": 0.0, "std": 0.0}
    assert np_res == {"average": 0.0, "minimum": 0.0, "maximum": 0.0, "std": 0.0}


def test_calculate_efficiency_score_deterministic() -> None:
    score1 = calculate_efficiency_score(15000.0)
    score2 = calculate_efficiency_score(15000.0)
    assert score1 == pytest.approx(score2)
    assert score1 > 0.0


def test_calculate_scores_threads() -> None:
    values = [12000.0, 34000.0, 56000.0, 78000.0]
    seq_res = calculate_scores_sequential(values)
    th_res = calculate_scores_threads(values, workers=2)
    assert th_res == pytest.approx(seq_res)


def test_calculate_scores_processes() -> None:
    values = [15000.0, 25000.0, 35000.0, 45000.0]
    seq_res = calculate_scores_sequential(values)
    proc_res = calculate_scores_processes(values, workers=2, chunksize=2)
    assert proc_res == pytest.approx(seq_res)


def test_thread_safe_counter_concurrency() -> None:
    counter = ThreadSafeCounter()

    def worker() -> None:
        for _ in range(500):
            counter.increment(1)

    threads = [Thread(target=worker) for _ in range(8)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert counter.value == 4000
    counter.reset()
    assert counter.value == 0


def test_unsafe_counter() -> None:
    counter = UnsafeCounter()
    counter.increment(5)
    assert counter.value == 5


def test_caching_and_invalidation() -> None:
    invalidate_brand_statistics_cache()
    info_before = cached_brand_statistics.cache_info()

    res1 = cached_brand_statistics("Porsche", version=1)
    res2 = cached_brand_statistics("Porsche", version=1)
    info_after = cached_brand_statistics.cache_info()

    assert res1 == res2
    assert info_after.hits == info_before.hits + 1

    res3 = cached_brand_statistics("Porsche", version=2)
    assert res3 is not None
    info_v2 = cached_brand_statistics.cache_info()
    assert info_v2.misses == info_after.misses + 1

    invalidate_brand_statistics_cache()
    info_cleared = cached_brand_statistics.cache_info()
    assert info_cleared.currsize == 0


def test_load_files_parallel(tmp_path: Path) -> None:
    files: list[Path] = []
    for i in range(5):
        p = tmp_path / f"catalog_part_{i}.txt"
        p.write_text(f"Car data chunk {i}", encoding="utf-8")
        files.append(p)

    seq_data = load_files_sequential(files)
    par_data = load_files_parallel(files, workers=3)

    assert par_data == seq_data
    assert len(par_data) == 5


def test_profiling_utilities() -> None:
    prices = generate_sample_prices(100, seed=123)
    stats = run_cprofile(statistics_python, prices)
    assert isinstance(stats, pstats.Stats)

    res, curr, peak = measure_memory_and_peak(statistics_numpy, prices)
    assert "average" in res
    assert peak >= 0.0

    name, elapsed, _ = benchmark("test_bench", statistics_python, prices)
    assert name == "test_bench"
    assert elapsed >= 0.0

    mean_t = benchmark_repeated(statistics_python, prices, repeats=3)
    assert mean_t >= 0.0

    speedup = calculate_speedup(2.0, 1.0)
    assert speedup == 2.0
    assert calculate_speedup(1.0, 0.0) == 0.0

    assert get_system_cpu_count() >= 1
