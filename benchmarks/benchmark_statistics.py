from car_catalog.analytics import (
    generate_sample_prices,
    statistics_numpy,
    statistics_python,
)
from car_catalog.profiling import benchmark_repeated, calculate_speedup

def run_statistics_benchmark(count: int = 100_000, repeats: int = 5) -> dict[str, float]:
    prices = generate_sample_prices(count, seed=42)
    py_time = benchmark_repeated(statistics_python, prices, repeats=repeats)
    np_time = benchmark_repeated(statistics_numpy, prices, repeats=repeats)
    speedup = calculate_speedup(py_time, np_time)
    return {
        "dataset_size": float(count),
        "python_mean_s": py_time,
        "numpy_mean_s": np_time,
        "speedup": speedup,
    }

if __name__ == "__main__":
    res = run_statistics_benchmark()
    print(f"Dataset: {int(res['dataset_size'])}")
    print(f"Python: {res['python_mean_s']:.6f} s")
    print(f"NumPy:  {res['numpy_mean_s']:.6f} s")
    print(f"Speedup: {res['speedup']:.2f}x")
