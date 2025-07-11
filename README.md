# dynapydantic

[![CI](https://github.com/psalvaggio/dynapydantic/actions/workflows/ci.yml/badge.svg)](https://github.com/psalvaggio/dynapydantic/actions/workflows/ci.yml)
[![Pre-commit](https://github.com/psalvaggio/dynapydantic/actions/workflows/pre-commit.yml/badge.svg)](https://github.com/psalvaggio/dynapydantic/actions/workflows/pre-commit.yml)

`dynapydantic` is an extension to the [pydantic](https://pydantic.dev) Python
package that allow for dynamic tracking of `pydantic.BaseModel` subclasses.

Installation
--
This project can be installed via PyPI:
```
pip install dynapydantic
```

Usage
--
The core entity in this library is the `dynapydantic.TrackingGroup`:
```python
import dynapydantic
import pydantic

mygroup = dynapydantic.TrackingGroup(
    name="mygroup",
    discriminator_field=""
)
```
