"""Cold-start import benchmark, intended to be run as a standalone script."""

import pyperf


def main() -> None:
    """Run pyperf in fresh interpreter subprocesses."""
    runner = pyperf.Runner()
    runner.bench_command("import dynapydantic", ["python", "-c", "import dynapydantic"])


if __name__ == "__main__":
    main()
