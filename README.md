# dynapydantic

[![CI](https://github.com/psalvaggio/dynapydantic/actions/workflows/ci.yml/badge.svg)](https://github.com/psalvaggio/dynapydantic/actions/workflows/ci.yml)
[![Pre-commit](https://github.com/psalvaggio/dynapydantic/actions/workflows/pre-commit.yml/badge.svg)](https://github.com/psalvaggio/dynapydantic/actions/workflows/pre-commit.yml)

This is a demonstration about how `pydantic` models can track their subclasses
and round-trip through serialization, both within the package in which they are
defined and in other packages via `pluggy`.

This package is not intended for public use yet. It's strictly a
proof-of-concept.
