from car_catalog.analytics import (
    calculate_scores_sequential,
    generate_sample_prices,
)
from car_catalog.parallel import calculate_scores_threads
from car_catalog.profiling import benchmark_repeated, calculate_speedup

def run_threads_benchmark(
    count: int = 10_000, workers_list: list[int] | None = None
) -> list[dict[str, float]]:
    if workers_list is None:
        workers_list = [1, 2, 4, 8]
    prices = generate_sample_prices(count, seed=42)
    baseline_time = benchmark_repeated(calculate_scores_sequential, prices, repeats=3)
    results: list[dict[str, float]] = [
        {
            "workers": 0.0,
            "mean_time_s": baseline_time,
            "speedup": 1.0,
        }
    ]
    for w in workers_list:
        t_w = benchmark_repeated(calculate_scores_threads, prices, workers=w, repeats=3)
        results.append(
            {
                "workers": float(w),
                "mean_time_s": t_w,
                "speedup": calculate_speedup(baseline_time, t_w),
            }
        )
    return results

if __name__ == "__main__":
    for row in run_threads_benchmark():
        w = int(row["workers"])
        label = "Sequential" if w == 0 else f"Threads {w}w"
        print(f"{label:15}: {row['mean_time_s']:.4f} s | Speedup: {row['speedup']:.2f}x")
