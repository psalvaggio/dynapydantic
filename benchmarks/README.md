# Benchmarks

Install the benchmark extra and run the suite locally with:

```sh
uv sync --dev
uv run pytest benchmarks/ --codspeed
```

The modules measure registration and union-construction scaling, validation and
serialization across registry sizes, Pydantic union modes, union realization
timing, recursive models, plugin loading, and cold-start import time. The
baseline comparison places hand-written discriminated unions beside equivalent
dynapydantic models for validation and serialization. Run the import benchmark
separately with `uv run python benchmarks/bench_import_time.py`; it uses pyperf
and fresh interpreters rather than pytest-codspeed.

Pull-request runs are sent to the [CodSpeed dashboard](https://codspeed.io/)
for historical performance trends.

## Interpreting the results

For the clearest estimate of library overhead, use
`bench_baseline_comparison.py`. At each registry size, compare the dynamic
and manual rows for the same operation and calculate:

```text
relative cost = dynapydantic time / manual time
overhead      = (relative cost - 1) * 100%
```

For example, `1.25x` means the dynamic operation took approximately 25% more
time than the hand-written discriminated union. The comparison measures
steady-state validation or serialization. Model creation, subclass
registration, union construction, and schema compilation are performed before
timing, so they are not included in that ratio.

To isolate validation-time union overhead, use
`bench_realization_timing.py`: compare the `validation` row with
`model-construction` at the same payload and subclass count. The difference is
the cost of checking the current registry generation, reusing (or rebuilding)
the cached adapter, and validating through it on each call. The `immediate`
row is a reference for an explicitly realized union, not a manual
implementation baseline. The incremental-rebuild test is
a separate workload that includes repeated schema rebuilds as subclasses are
registered.

The union-mode benchmarks answer a different question: they measure Pydantic's
discriminated, smart, and left-to-right search/error behavior after a union has
already been created. Successful and failing validation paths should not be
combined. Focus on ratios and scaling trends at equal variant counts; absolute
times vary with Python, Pydantic, hardware, and model shape.
