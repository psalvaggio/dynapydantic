# dynapydantic benchmarks

This suite measures dynapydantic's marginal overhead over equivalent hand-rolled
discriminated Pydantic unions.

The generated models all have the a realistic number of fields and a nested
model to emulate a realistic use case.

## Running

Install the locked development environment, then write a machine-readable
result file:

```sh
uv sync --locked --all-extras --dev
uv run pytest benchmarks/ --codspeed
```

To summarize the results, use:

```sh
uv run python -m benchmarks.summarize "$(ls -t .codspeed/*.json | head -n 1)"
```

The first table reports dynapydantic overhead for registration and
model-construction time over the hand-rolled baseline. The second reports
validation-time overhead over the same baseline implementations. Each table
report the median time and the inter-quartile range (IQR), both as absolute and
relative timings.

Python and JSON validation are reported separately. Validation-time realization
is expected to be especially visible for JSON because its field adapter must
re-encode the already decoded field before validating it as JSON.
