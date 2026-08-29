# Benchmarks

Install the benchmark extra and run the suite locally with:

```sh
uv sync --dev
uv run pytest benchmarks/ --benchmark-only
```

The modules measure registration and union-construction scaling, validation and
serialization across registry sizes, Pydantic union modes, union realization
timing, recursive models, plugin loading, and cold-start import time. The
baseline comparison places hand-written discriminated unions beside equivalent
dynapydantic models for validation and serialization. Run the import benchmark
separately with `uv run python benchmarks/bench_import_time.py`; it uses pyperf
and fresh interpreters rather than pytest-benchmark.

Pull-request runs are sent to the [CodSpeed dashboard](https://codspeed.io/)
for historical performance trends.
