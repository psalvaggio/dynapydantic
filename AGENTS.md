# Repository Guidelines

## Project Structure & Module Organization

`src/dynapydantic/` contains the installable package. Core model tracking,
polymorphic validation, annotations, and version handling are split into
focused modules; update public exports in `src/dynapydantic/__init__.py` when
adding public APIs. `tests/` contains the pytest suite, including example
distributions under `tests/example/` for plugin behavior. User-facing
documentation lives in `README.md` and `docs/`; `mkdocs.yml` configures the
documentation site. `noxfile.py` defines the supported Python/Pydantic test
matrix.

## Build, Test, and Development Commands

Use Python 3.10+ and install the locked development environment with:

```sh
uv sync --locked --all-extras --dev
```

Common checks are:

```sh
uv run pytest tests                 # Run tests and generate HTML coverage
uv run nox                          # Run the full Python/Pydantic matrix
uv run ruff check                   # Lint Python files
uv run ruff format --check         # Verify formatting
uv run pyrefly check                # Run static type checking
uv run prek run --all-files         # Run all pre-commit checks
uv build                            # Build source and wheel distributions
```

Pass focused pytest paths or options after `pytest`, for example
`uv run pytest tests/test_plugins.py -q`.

## Coding Style & Naming Conventions

Format Python with Ruff and follow its configured `ALL` lint rules and NumPy
docstring convention. Use four-space indentation, `snake_case` for functions
and modules, `PascalCase` for classes, and type annotations for public and
internal APIs. Keep implementation modules focused and preserve the package's
Python 3.10 compatibility (the generics-specific test targets Python 3.12).

## Testing Guidelines

Tests use pytest and should be added under `tests/` as `test_*.py`, with test
functions named `test_<behavior>`. Cover normal validation, serialization,
inheritance, version compatibility, and plugin edge cases where relevant.
Run the focused test first, then `uv run pytest tests`; use `uv run nox` for
changes affecting supported Python or Pydantic versions.
