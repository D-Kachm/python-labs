import csv
from pathlib import Path
from statistics import mean
from threading import Thread
import time
from typing import Any
from car_catalog.analytics import (
    cached_brand_statistics,
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
)
from car_catalog.profiling import (
    calculate_speedup,
    get_system_cpu_count,
    measure_memory_and_peak,
    run_cprofile,
)

RESULTS_CSV = Path("benchmarks/results/benchmark_results.csv")


def run_experiment_1_profiling_and_bottleneck() -> None:
    print("\n" + "=" * 80)
    print("ЕКСПЕРИМЕНТ 1: ВИЯВЛЕННЯ ВУЗЬКИХ МІСЦЬ (BOTTLENECK DETECTION) ЧЕРЕЗ cProfile ТА tracemalloc")
    print("=" * 80)
    prices = generate_sample_prices(10_000, seed=42)
    print(f"Згенеровано тестовий набір із {len(prices)} цін автомобілів.")

    print("\n1.1. Аналіз профілю виконання (cProfile):")
    stats = run_cprofile(calculate_scores_sequential, prices)
    stats.sort_stats("cumulative")
    stats.print_stats(10)

    print("\n1.2. Аналіз споживання оперативної пам'яті (tracemalloc):")
    _, curr_py, peak_py = measure_memory_and_peak(statistics_python, prices)
    print(f"   Python Baseline Stats: Current = {curr_py:.2f} KB | Peak = {peak_py:.2f} KB")
    _, curr_np, peak_np = measure_memory_and_peak(statistics_numpy, prices)
    print(f"   NumPy Vectorized Stats: Current = {curr_np:.2f} KB | Peak = {peak_np:.2f} KB")
    print(f"   Зменшення пікового споживання пам'яті: {peak_py / peak_np if peak_np > 0 else 1.0:.2f}x")


def run_experiment_2_concurrency_and_locks() -> None:
    print("\n" + "=" * 80)
    print("ЕКСПЕРИМЕНТ 2: СИНХРОНІЗАЦІЯ ПОТОКІВ (LOCK) ТА УСУНЕННЯ RACE CONDITIONS")
    print("=" * 80)

    safe_counter = ThreadSafeCounter()
    unsafe_counter = UnsafeCounter()

    def safe_worker() -> None:
        for _ in range(2000):
            safe_counter.increment(1)

    def unsafe_worker() -> None:
        for _ in range(2000):
            unsafe_counter.increment(1)

    threads_safe = [Thread(target=safe_worker) for _ in range(10)]
    for t in threads_safe:
        t.start()
    for t in threads_safe:
        t.join()

    threads_unsafe = [Thread(target=unsafe_worker) for _ in range(10)]
    for t in threads_unsafe:
        t.start()
    for t in threads_unsafe:
        t.join()

    print("Очікуване значення лічильника (10 потоків * 2000 ітерацій): 20000")
    print(f"ThreadSafeCounter (із Lock):   {safe_counter.value} (коректно)")
    print(f"UnsafeCounter (без Lock):      {unsafe_counter.value} (стан гонитви / race condition)")


def run_experiment_3_caching_and_invalidation() -> None:
    print("\n" + "=" * 80)
    print("ЕКСПЕРИМЕНТ 3: КЕШУВАННЯ СТАТИСТИКИ АВТОВИРОБНИКІВ ТА АНАЛІЗ CACHE INVALIDATION")
    print("=" * 80)
    invalidate_brand_statistics_cache()

    start = time.perf_counter()
    cached_brand_statistics("BMW", version=1)
    t_cold = time.perf_counter() - start

    start = time.perf_counter()
    cached_brand_statistics("BMW", version=1)
    t_warm = time.perf_counter() - start

    info = cached_brand_statistics.cache_info()
    print(f"Холодний виклик (Cold Cache, обчислення):   {t_cold:.6f} s")
    print(f"Гарячий виклик (Warm Cache, пам'ять):       {t_warm:.6f} s")
    print(f"Коефіцієнт прискорення завдяки кешуванню:   {calculate_speedup(t_cold, t_warm):.2f}x")
    print(f"Статистика LRU: hits={info.hits}, misses={info.misses}, size={info.currsize}/{info.maxsize}")

    start = time.perf_counter()
    cached_brand_statistics("BMW", version=2)
    t_invalidated = time.perf_counter() - start
    print(f"Після зміни версії (Cache Invalidation):    {t_invalidated:.6f} s (новий промах / miss)")


def run_experiment_4_benchmark_matrix() -> list[dict[str, Any]]:
    print("\n" + "=" * 80)
    print("ЕКСПЕРИМЕНТ 4: ПОВНА МАТРИЦЯ БЕНЧМАРКІВ (3 РОЗМІРИ DATASET x 4 КОНФІГУРАЦІЇ WORKERS)")
    print("=" * 80)

    cpu_count = get_system_cpu_count()
    print(f"Доступно CPU-ядер у системі: {cpu_count}")

    dataset_sizes = [10_000, 100_000, 200_000]
    workers_configs = [1, 2, 4, 8]
    all_rows: list[dict[str, Any]] = []

    header = f"{'Dataset':<10} | {'Method':<24} | {'Workers':<7} | {'Run 1':<8} | {'Run 2':<8} | {'Run 3':<8} | {'Mean, s':<9} | {'Peak, KB':<9} | {'Speedup':<8}"
    print(header)
    print("-" * len(header))

    for size in dataset_sizes:
        prices = generate_sample_prices(size, seed=42)
        sample = prices[: min(size, 10_000)]

        runs_seq: list[float] = []
        for _ in range(3):
            s = time.perf_counter()
            calculate_scores_sequential(sample)
            runs_seq.append(time.perf_counter() - s)
        mean_seq = mean(runs_seq)
        _, _, peak_seq = measure_memory_and_peak(calculate_scores_sequential, sample)

        row_seq = {
            "dataset": size,
            "method": "Sequential Baseline",
            "workers": 1,
            "run1": runs_seq[0],
            "run2": runs_seq[1],
            "run3": runs_seq[2],
            "mean": mean_seq,
            "peak_kb": peak_seq,
            "speedup": 1.0,
        }
        all_rows.append(row_seq)
        print(
            f"{size:<10} | {'Sequential Baseline':<24} | {1:<7} | {runs_seq[0]:<8.4f} | {runs_seq[1]:<8.4f} | {runs_seq[2]:<8.4f} | {mean_seq:<9.4f} | {peak_seq:<9.1f} | {'1.00x':<8}"
        )

        for w in workers_configs:
            runs_th: list[float] = []
            for _ in range(3):
                s = time.perf_counter()
                calculate_scores_threads(sample, workers=w)
                runs_th.append(time.perf_counter() - s)
            mean_th = mean(runs_th)
            _, _, peak_th = measure_memory_and_peak(calculate_scores_threads, sample, workers=w)
            sp_th = calculate_speedup(mean_seq, mean_th)
            row_th = {
                "dataset": size,
                "method": f"ThreadPoolExecutor-{w}w",
                "workers": w,
                "run1": runs_th[0],
                "run2": runs_th[1],
                "run3": runs_th[2],
                "mean": mean_th,
                "peak_kb": peak_th,
                "speedup": sp_th,
            }
            all_rows.append(row_th)
            print(
                f"{size:<10} | {f'ThreadPoolExecutor-{w}w':<24} | {w:<7} | {runs_th[0]:<8.4f} | {runs_th[1]:<8.4f} | {runs_th[2]:<8.4f} | {mean_th:<9.4f} | {peak_th:<9.1f} | {f'{sp_th:.2f}x':<8}"
            )

        for w in workers_configs:
            runs_pr: list[float] = []
            for _ in range(3):
                s = time.perf_counter()
                calculate_scores_processes(sample, workers=w, chunksize=100)
                runs_pr.append(time.perf_counter() - s)
            mean_pr = mean(runs_pr)
            _, _, peak_pr = measure_memory_and_peak(calculate_scores_processes, sample, workers=w, chunksize=100)
            sp_pr = calculate_speedup(mean_seq, mean_pr)
            row_pr = {
                "dataset": size,
                "method": f"ProcessPoolExecutor-{w}w",
                "workers": w,
                "run1": runs_pr[0],
                "run2": runs_pr[1],
                "run3": runs_pr[2],
                "mean": mean_pr,
                "peak_kb": peak_pr,
                "speedup": sp_pr,
            }
            all_rows.append(row_pr)
            print(
                f"{size:<10} | {f'ProcessPoolExecutor-{w}w':<24} | {w:<7} | {runs_pr[0]:<8.4f} | {runs_pr[1]:<8.4f} | {runs_pr[2]:<8.4f} | {mean_pr:<9.4f} | {peak_pr:<9.1f} | {f'{sp_pr:.2f}x':<8}"
            )

        runs_py_st: list[float] = []
        for _ in range(3):
            s = time.perf_counter()
            statistics_python(prices)
            runs_py_st.append(time.perf_counter() - s)
        mean_py_st = mean(runs_py_st)
        _, _, peak_py_st = measure_memory_and_peak(statistics_python, prices)

        row_py_st = {
            "dataset": size,
            "method": "Python Stats (Loops)",
            "workers": 1,
            "run1": runs_py_st[0],
            "run2": runs_py_st[1],
            "run3": runs_py_st[2],
            "mean": mean_py_st,
            "peak_kb": peak_py_st,
            "speedup": 1.0,
        }
        all_rows.append(row_py_st)
        print(
            f"{size:<10} | {'Python Stats (Loops)':<24} | {1:<7} | {runs_py_st[0]:<8.5f} | {runs_py_st[1]:<8.5f} | {runs_py_st[2]:<8.5f} | {mean_py_st:<9.5f} | {peak_py_st:<9.1f} | {'1.00x':<8}"
        )

        runs_np_st: list[float] = []
        for _ in range(3):
            s = time.perf_counter()
            statistics_numpy(prices)
            runs_np_st.append(time.perf_counter() - s)
        mean_np_st = mean(runs_np_st)
        _, _, peak_np_st = measure_memory_and_peak(statistics_numpy, prices)
        sp_np_st = calculate_speedup(mean_py_st, mean_np_st)

        row_np_st = {
            "dataset": size,
            "method": "NumPy Stats (Vectorized)",
            "workers": 1,
            "run1": runs_np_st[0],
            "run2": runs_np_st[1],
            "run3": runs_np_st[2],
            "mean": mean_np_st,
            "peak_kb": peak_np_st,
            "speedup": sp_np_st,
        }
        all_rows.append(row_np_st)
        print(
            f"{size:<10} | {'NumPy Stats (Vectorized)':<24} | {1:<7} | {runs_np_st[0]:<8.5f} | {runs_np_st[1]:<8.5f} | {runs_np_st[2]:<8.5f} | {mean_np_st:<9.5f} | {peak_np_st:<9.1f} | {f'{sp_np_st:.2f}x':<8}"
        )
        print("-" * len(header))

    RESULTS_CSV.parent.mkdir(parents=True, exist_ok=True)
    with open(RESULTS_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "dataset",
                "method",
                "workers",
                "run1",
                "run2",
                "run3",
                "mean",
                "peak_kb",
                "speedup",
            ],
        )
        writer.writeheader()
        writer.writerows(all_rows)
    print(f"\nЕкспериментальні дані збережено в CSV: {RESULTS_CSV}")
    return all_rows


def main() -> None:
    print("=" * 80)
    print("ЛАБОРАТОРНА РОБОТА №9: ДОСЛІДЖЕННЯ ПАРАЛЕЛЬНОСТІ, ПРОЦЕСІВ ТА ОПТИМІЗАЦІЇ")
    print("=" * 80)
    run_experiment_1_profiling_and_bottleneck()
    run_experiment_2_concurrency_and_locks()
    run_experiment_3_caching_and_invalidation()
    run_experiment_4_benchmark_matrix()
    print("\nУсі 4 експерименти Лабораторної №9 виконано успішно.")


if __name__ == "__main__":
    main()
