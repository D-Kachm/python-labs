import csv
from pathlib import Path
from car_catalog.analytics import (
    calculate_scores_sequential,
    generate_sample_prices,
    statistics_numpy,
    statistics_python,
)
from car_catalog.parallel import (
    calculate_scores_processes,
    calculate_scores_threads,
)
from car_catalog.profiling import (
    benchmark_repeated,
    calculate_speedup,
    measure_memory_and_peak,
)

RESULTS_DIR = Path("benchmarks/results")
RESULTS_CSV = RESULTS_DIR / "benchmark_results.csv"

def run_full_benchmark_suite(
    dataset_sizes: list[int] | None = None,
    workers_list: list[int] | None = None,
) -> list[dict[str, object]]:
    if dataset_sizes is None:
        dataset_sizes = [10_000, 100_000, 200_000]
    if workers_list is None:
        workers_list = [1, 2, 4, 8]

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    rows: list[dict[str, object]] = []

    for size in dataset_sizes:
        prices = generate_sample_prices(size, seed=42)
        _, _, base_peak = measure_memory_and_peak(calculate_scores_sequential, prices[:min(size, 10_000)])
        t_base = benchmark_repeated(calculate_scores_sequential, prices[:min(size, 10_000)], repeats=3)
        rows.append(
            {
                "experiment": "CPU-bound Baseline",
                "data_size": size,
                "workers": 1,
                "mean_time_s": round(t_base, 5),
                "peak_memory_kb": round(base_peak, 2),
                "speedup": 1.0,
            }
        )

        for w in workers_list:
            _, _, th_peak = measure_memory_and_peak(
                calculate_scores_threads, prices[:min(size, 10_000)], workers=w
            )
            t_th = benchmark_repeated(
                calculate_scores_threads, prices[:min(size, 10_000)], workers=w, repeats=3
            )
            rows.append(
                {
                    "experiment": f"ThreadPoolExecutor-{w}w",
                    "data_size": size,
                    "workers": w,
                    "mean_time_s": round(t_th, 5),
                    "peak_memory_kb": round(th_peak, 2),
                    "speedup": round(calculate_speedup(t_base, t_th), 2),
                }
            )

        for w in workers_list:
            _, _, pr_peak = measure_memory_and_peak(
                calculate_scores_processes,
                prices[:min(size, 10_000)],
                workers=w,
                chunksize=100,
            )
            t_pr = benchmark_repeated(
                calculate_scores_processes,
                prices[:min(size, 10_000)],
                workers=w,
                chunksize=100,
                repeats=3,
            )
            rows.append(
                {
                    "experiment": f"ProcessPoolExecutor-{w}w",
                    "data_size": size,
                    "workers": w,
                    "mean_time_s": round(t_pr, 5),
                    "peak_memory_kb": round(pr_peak, 2),
                    "speedup": round(calculate_speedup(t_base, t_pr), 2),
                }
            )

        _, _, py_stat_peak = measure_memory_and_peak(statistics_python, prices)
        t_py_stat = benchmark_repeated(statistics_python, prices, repeats=5)
        _, _, np_stat_peak = measure_memory_and_peak(statistics_numpy, prices)
        t_np_stat = benchmark_repeated(statistics_numpy, prices, repeats=5)

        rows.append(
            {
                "experiment": "Python Stats (Loops)",
                "data_size": size,
                "workers": 1,
                "mean_time_s": round(t_py_stat, 6),
                "peak_memory_kb": round(py_stat_peak, 2),
                "speedup": 1.0,
            }
        )
        rows.append(
            {
                "experiment": "NumPy Stats (Vectorized)",
                "data_size": size,
                "workers": 1,
                "mean_time_s": round(t_np_stat, 6),
                "peak_memory_kb": round(np_stat_peak, 2),
                "speedup": round(calculate_speedup(t_py_stat, t_np_stat), 2),
            }
        )

    with open(RESULTS_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "experiment",
                "data_size",
                "workers",
                "mean_time_s",
                "peak_memory_kb",
                "speedup",
            ],
        )
        writer.writeheader()
        writer.writerows(rows)

    return rows

if __name__ == "__main__":
    suite_results = run_full_benchmark_suite([10_000, 100_000], [1, 2, 4, 8])
    print(f"Results written to {RESULTS_CSV}")
