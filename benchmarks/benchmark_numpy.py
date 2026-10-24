from car_catalog.analytics import (
    generate_sample_prices,
    statistics_numpy,
    statistics_python,
)
from car_catalog.profiling import (
    benchmark_repeated,
    calculate_speedup,
    measure_memory_and_peak,
)

def run_numpy_benchmark(count: int = 100_000) -> dict[str, float]:
    prices = generate_sample_prices(count, seed=42)
    _, _, py_peak = measure_memory_and_peak(statistics_python, prices)
    _, _, np_peak = measure_memory_and_peak(statistics_numpy, prices)
    py_time = benchmark_repeated(statistics_python, prices, repeats=5)
    np_time = benchmark_repeated(statistics_numpy, prices, repeats=5)
    return {
        "dataset_size": float(count),
        "python_time_s": py_time,
        "numpy_time_s": np_time,
        "speedup": calculate_speedup(py_time, np_time),
        "python_peak_kb": py_peak,
        "numpy_peak_kb": np_peak,
    }

if __name__ == "__main__":
    res = run_numpy_benchmark()
    print(f"NumPy Benchmark (N={int(res['dataset_size'])}):")
    print(f"Python: {res['python_time_s']:.6f} s (Peak: {res['python_peak_kb']:.2f} KB)")
    print(f"NumPy:  {res['numpy_time_s']:.6f} s (Peak: {res['numpy_peak_kb']:.2f} KB)")
    print(f"Speedup: {res['speedup']:.2f}x")
