"""Print dynapydantic overhead results from pytest-benchmark JSON output.

Overhead means time added by dynapydantic relative to an equivalent hand-rolled
implementation.
"""

import argparse
import itertools
import json
import math
import sys
import typing as ty
from pathlib import Path

import dynapydantic

from .common import (
    DiscriminatorField,
    Implementation,
    ParsedTestId,
    PayloadCount,
    PayloadFormat,
    SubclassCount,
    UnionMode,
    union_realization_label,
)


class ResultsManifest:
    """Parsed benchmark statistics from a pytest-benchmark report."""

    def __init__(self, filename: Path) -> None:
        data = json.loads(filename.read_text(encoding="utf-8"))
        self.benchmarks: list[tuple[ParsedTestId, dict[str, float]]] = [
            (ParsedTestId.from_id(b["name"]), b["stats"]) for b in data["benchmarks"]
        ]

    def stats(  # noqa: PLR0913
        self,
        test_name: str,
        *,
        implementation: Implementation,
        union_mode: UnionMode,
        subclass_count: SubclassCount,
        realization: dynapydantic.UnionRealization | None = None,
        discriminator_field: DiscriminatorField | None = None,
        payload_count: PayloadCount | None = None,
        payload_format: PayloadFormat | None = None,
    ) -> dict[str, float]:
        """Find statistics matching a benchmark case.

        Parameters
        ----------
        test_name
            Name of the benchmark function.
        implementation
            Implementation used by the benchmark case.
        union_mode
            Union mode used by the benchmark case.
        subclass_count
            Number of concrete subclasses in the benchmark case.
        realization
            Dynapydantic union realization strategy, when applicable.
        discriminator_field
            Discriminator field strategy, when applicable.
        payload_count
            Number of validation payloads, when applicable.
        payload_format
            Validation input format, when applicable.

        Returns
        -------
        dict[str, float]
            The recorded benchmark statistics.

        Raises
        ------
        ValueError
            If no matching benchmark record exists.
        """
        for params, stats in self.benchmarks:
            if (
                test_name != params.test_name
                or implementation != params.implementation
                or union_mode != params.union_mode
                or realization != params.realization
                or discriminator_field != params.discriminator_field
                or subclass_count != params.subclass_count
                or payload_count != params.payload_count
                or payload_format != params.payload_format
            ):
                continue
            return stats

        msg = "Unable to locate the requested record"
        raise ValueError(msg)


def _median_and_iqr(
    stats: dict[str, float],
) -> tuple[float, float]:
    return stats["median_ns"] / 1e9, (stats["q3_ns"] - stats["q1_ns"]) / 1e9


def _duration(seconds_mean: float, seconds_pm: float) -> str:
    """Format a duration using the most readable supported unit.

    Parameters
    ----------
    seconds_mean
        Mean or median duration in seconds.
    seconds_pm
        Uncertainty or spread in seconds.

    Returns
    -------
    str
        A formatted duration in seconds, milliseconds, or microseconds.
    """
    magnitude = abs(seconds_mean)
    if magnitude >= 0.1:  # noqa: PLR2004
        scale, unit = 1, "s"
    elif magnitude >= 1e-4:  # noqa: PLR2004
        scale, unit = 1e3, "ms"
    else:
        scale, unit = 1e6, "us"
    return f"{seconds_mean * scale:.3f} ± {seconds_pm * scale:.3f} {unit}"


def _append_validation_table(
    lines: list[str],
    results: ResultsManifest,
) -> None:
    """Append the validation overhead table to ``lines``.

    Parameters
    ----------
    lines
        Output lines to extend with the generated table.
    results
        Parsed benchmark statistics used to populate the table.
    """
    test_name = "test_validation"
    subclass_counts = list(
        {
            params.subclass_count
            for params, _ in results.benchmarks
            if params.test_name == test_name
        }
    )
    if len(subclass_counts) != 1:
        msg = f"All {test_name} tests must have the same subclass count"
        raise RuntimeError(msg)
    subclass_count = subclass_counts[0]

    distinct_n = sorted(
        {
            ty.cast("PayloadCount", params.payload_count)
            for params, _ in results.benchmarks
            if params.test_name == test_name
        }
    )
    scenarios = list(
        itertools.product((PayloadFormat.PYTHON, PayloadFormat.JSON), distinct_n)
    )

    lines.extend(
        [
            "",
            (
                "## Validation overhead per validation (median ± IQR; "
                f'{subclass_count} subclasses) <a id="validation"></a>'
            ),
            "",
            '<table class="benchmark-table">',
            "  <thead>",
            "    <tr>",
            '      <th rowspan="2" scope="col">Mode</th>',
            *(
                f'      <th scope="col">{fmt.title()} (N={count})</th>'
                for fmt, count in scenarios
            ),
            "    </tr>",
            "  </thead>",
            "  <tbody>",
        ]
    )

    configs = sorted(
        {
            (params.union_mode, params.realization)
            for params, stats in results.benchmarks
            if params.test_name == test_name
            and params.implementation == Implementation.DYNAPYDANTIC
        },
        key=str,
    )

    for union_mode, realization in configs:
        lines.append("    <tr>")
        lines.append(
            '      <th scope="row">'
            f"{union_mode.value.title()} "
            f"{union_realization_label(realization)}"
            "</th>"
        )

        for fmt, count in scenarios:
            median, iqr = _median_and_iqr(
                results.stats(
                    test_name,
                    implementation=Implementation.DYNAPYDANTIC,
                    union_mode=union_mode,
                    subclass_count=subclass_count,
                    realization=realization,
                    payload_count=count,
                    payload_format=fmt,
                )
            )
            baseline_median, baseline_iqr = _median_and_iqr(
                results.stats(
                    test_name,
                    implementation=Implementation.MANUAL,
                    union_mode=union_mode,
                    subclass_count=subclass_count,
                    payload_count=count,
                    payload_format=fmt,
                )
            )

            overhead_median = (median - baseline_median) / count
            overhead_iqr = math.hypot(iqr, baseline_iqr) / count
            relative_median = overhead_median / (baseline_median / count)
            relative_iqr = abs(relative_median) * math.hypot(
                overhead_iqr / overhead_median, baseline_iqr / baseline_median
            )
            lines.append(
                "      <td>"
                f"{_duration(overhead_median, overhead_iqr)}<br>"
                f"{relative_median * 100:.2f}% ± {relative_iqr * 100:.2f}%"
                "</td>"
            )
        lines.append("    </tr>")

    lines.extend(["  </tbody>", "</table>"])


def _append_registration_table(lines: list[str], results: ResultsManifest) -> None:
    """Append the registration overhead table to ``lines``.

    Parameters
    ----------
    lines
        Output lines to extend with the generated table.
    results
        Parsed benchmark statistics used to populate the table.
    """
    test_name = "test_registration"
    distinct_n = sorted(
        {
            params.subclass_count
            for params, _ in results.benchmarks
            if params.test_name == test_name
        }
    )

    lines += [
        '## Class hierarchy creation (median ± IQR) <a id="registration"></a>',
        "",
        '<table class="benchmark-table">',
        "  <thead>",
        "    <tr>",
        '      <th rowspan="2">Mode</th>',
        f'     <th colspan="{len(distinct_n)}" scope="colgroup">Subclass Count</th>',
        "    </tr>",
        "    <tr>",
        *[f"      <th>{n}</th>" for n in distinct_n],
        "    </tr>",
        "  </thead>",
        "  <tbody>",
    ]

    for union_mode, realization, disc_field in (
        (
            UnionMode.DISCRIMINATED,
            dynapydantic.UnionRealization.MODEL_CONSTRUCTION,
            DiscriminatorField.EXPLICIT,
        ),
        (
            UnionMode.DISCRIMINATED,
            dynapydantic.UnionRealization.VALIDATION,
            DiscriminatorField.EXPLICIT,
        ),
        (
            UnionMode.DISCRIMINATED,
            dynapydantic.UnionRealization.MODEL_CONSTRUCTION,
            DiscriminatorField.INJECTED,
        ),
        (
            UnionMode.DISCRIMINATED,
            dynapydantic.UnionRealization.VALIDATION,
            DiscriminatorField.INJECTED,
        ),
        (UnionMode.SMART, dynapydantic.UnionRealization.MODEL_CONSTRUCTION, None),
        (UnionMode.SMART, dynapydantic.UnionRealization.VALIDATION, None),
    ):
        injected_label = (
            "<br>Injected" if disc_field == DiscriminatorField.INJECTED else ""
        )
        lines += [
            "    <tr>",
            (
                f"      <th>{union_mode.value.title()} "
                f"{union_realization_label(realization)}{injected_label}</th>"
            ),
        ]
        for n in distinct_n:
            base_median, base_iqr = _median_and_iqr(
                results.stats(
                    test_name,
                    implementation=Implementation.MANUAL,
                    union_mode=union_mode,
                    subclass_count=n,
                )
            )
            case_median, case_iqr = _median_and_iqr(
                results.stats(
                    test_name,
                    implementation=Implementation.DYNAPYDANTIC,
                    union_mode=union_mode,
                    subclass_count=n,
                    realization=realization,
                    discriminator_field=disc_field,
                )
            )
            overhead_median = case_median - base_median
            overhead_iqr = math.hypot(case_iqr, base_iqr)
            rel_median = overhead_median / base_median
            rel_iqr = abs(rel_median) * math.hypot(
                overhead_iqr / overhead_median, base_iqr / base_median
            )
            lines.append(
                f"      <td>{_duration(overhead_median, overhead_iqr)}<br>"
                f"{rel_median * 100:.2f}% ± {rel_iqr * 100:.2f}%</td>"
            )
        lines.append("    </tr>")
    lines.extend(["  </tbody>", "</table>"])


def main() -> None:
    """Load benchmark JSON and print Markdown overhead tables."""
    parser = argparse.ArgumentParser()
    parser.add_argument("path", help="pytest-benchmark --benchmark-json output")
    args = parser.parse_args()

    results = ResultsManifest(Path(args.path))

    lines: list[str] = [
        "# `dynapydantic` Benchmarks",
        "",
        "### Legend",
        "* MC = Model-construction time union realization",
        "* VT = Validation-time union realization",
        "* Disc = Discriminated union",
        "* Smart = Smart union",
        "",
    ]

    _append_registration_table(lines, results)
    _append_validation_table(lines, results)

    sys.stdout.write("\n".join(lines) + "\n")


if __name__ == "__main__":
    main()
