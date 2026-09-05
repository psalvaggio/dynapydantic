# dynapydantic benchmarks

This suite measures dynapydantic's marginal overhead over an equivalent
hand-rolled discriminated Pydantic union. It is not a general Pydantic
benchmark: the numbers do not characterize absolute `pydantic-core`
performance, serialization or `model_dump` cost, or memory usage.

The generated models all have the same four ordinary fields (`int`, `str`, and
`float`, plus a small nested model) and one string discriminator. Only the
number of concrete subclasses varies: 5, 25, and 100. Validation uses a
deterministically selected interior subclass so the discriminator lookup is
not always measured at the first branch.

## Running

Install the locked development environment, then write a machine-readable
result file:

```sh
uv sync --locked --all-extras --dev
uv run pytest benchmarks/ --benchmark-json=results.json
```

The same benchmarks can be checked locally with CodSpeed using
`uv run pytest benchmarks/ --codspeed`; CI runs this mode through the
CodSpeed GitHub Action. CodSpeed writes its raw report under `.codspeed/`.
That report is normalized for `summarize.py` before the CI comment is made.

The registration benchmark uses `benchmark.pedantic` with one fresh hierarchy
per timed round. It includes dynapydantic subclasses that either receive an
injected discriminator or declare their `Literal` discriminator field before
registration. Validation builds a fresh hierarchy in `benchmark.pedantic` setup
for every benchmark round, with 100 explicit timed rounds per case. Setup is
excluded from timing, but this ensures that the `first` case includes first-use
validation-time adapter construction and the `1000` case can amortize that
construction across the batch. Fresh dynamic modules, base classes, tracking
groups, and subclasses prevent registry reuse between rounds. Explicit rounds
keep the cold-start cases from collapsing to one sample when the benchmark
runner is configured with a one-round minimum.

To print the summary:

```sh
uv run python -m benchmarks.summarize results.json
```

The first table reports dynapydantic model-construction-mode validation divided
by the hand-rolled baseline. The second reports validation-time realization
divided by model-construction-time realization. The registration table reports
absolute median times using the most readable unit (seconds, milliseconds, or
microseconds) for the hand-rolled baseline, both
dynapydantic registration paths, and the gap between injected and declared
discriminator fields. The JSON file can also be compared across commits with
`pytest-benchmark compare` (for example, compare two saved benchmark JSON
files).

Python and JSON validation are reported separately. Validation-time realization
is expected to be especially visible for JSON because its field adapter must
re-encode the already decoded field before validating it as JSON.

Non-discriminated `smart` and `left_to_right` unions, plugin discovery
overhead, memory profiling, and serialization benchmarks are intentionally out
of scope. They are possible future extensions.
