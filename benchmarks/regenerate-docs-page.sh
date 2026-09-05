#!/usr/bin/env bash

set -eou pipefail

cd -- "$( dirname -- "${BASH_SOURCE[0]}" )/.." &> /dev/null

uv run pytest benchmarks/ --codspeed

reports=(.codspeed/*.json)
if ((${#reports[@]} == 0)); then
    echo "No CodSpeed report found in .codspeed" >&2
    exit 1
fi

latest_report=$(ls -t "${reports[@]}" | head -n 1)
uv run python -m benchmarks.summarize "$latest_report" > docs/benchmarks.md
