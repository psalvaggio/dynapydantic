# dynapydantic

[![CI](https://github.com/psalvaggio/dynapydantic/actions/workflows/ci.yml/badge.svg)](https://github.com/psalvaggio/dynapydantic/actions/workflows/ci.yml)
[![Pre-commit](https://github.com/psalvaggio/dynapydantic/actions/workflows/pre-commit.yml/badge.svg)](https://github.com/psalvaggio/dynapydantic/actions/workflows/pre-commit.yml)
[![Docs](https://img.shields.io/badge/docs-Docs-blue?style=flat-square&logo=github&logoColor=white&link=https://psalvaggio.github.io/dynapydantic/dev/)](https://psalvaggio.github.io/dynapydantic/dev/)
[![PyPI - Version](https://img.shields.io/pypi/v/dynapydantic)](https://pypi.org/project/dynapydantic/)
[![Coverage Status](https://coveralls.io/repos/github/psalvaggio/dynapydantic/badge.svg?branch=main)](https://coveralls.io/github/psalvaggio/dynapydantic?branch=main)
[![Conda Version](https://img.shields.io/conda/v/conda-forge/dynapydantic)](https://anaconda.org/conda-forge/dynapydantic)

## Table of contents

- [When should I use this?](#when-should-i-use-this)
- [Quick start](#quick-start)
  - [Installation](#installation)
  - [Basic Example](#basic-example)
  - [Plugin discovery](#plugin-discovery)
- [Motivation](#motivation)
- [How it works](#how-it-works)
  - [`TrackingGroup`](#trackinggroup)
  - [`SubclassTrackingModel`](#subclasstrackingmodel)
  - [Alternative union methods](#alternative-union-methods)
  - [Union realization](#union-realization)
- [Caveats and Limitations](#caveats-and-limitations)
- [Testing](#testing)


Runtime polymorphic validation and serialization for
[Pydantic](https://pydantic.dev) models. `dynapydantic` lets Pydantic fields
accept, validate, and serialize dynamically-discovered models without
maintaining a manually-updated union.

### When should I use this?

| Use a regular union | Use `dynapydantic` |
| :-----------------: | :----------------: |
| Types are fixed and local | Types are extension points |
| You control every type | Types are scattered or come from plugins |
| Static typing is the priority | Runtime discovery is required |

`dynapydantic` eliminates the need to manually track all options in an
explicit union. It adds more value as this union becomes harder to maintain. It
becomes extremely valuable when such a union is impossible to write, such as
when doing so would introduce a ciruclar dependency or plugin discovery is
needed.


## Quick start

### Installation
This project can be installed via the PyPI or conda ecosystems:
```
pip install dynapydantic
conda install -c conda-forge dynapydantic
```

### Basic Example

```python
import dynapydantic
import pydantic

class Event(
    dynapydantic.SubclassTrackingModel,
    discriminator_field="type",
    discriminator_value_generator=lambda cls: cls.__name__,
):
    pass

class UserCreated(Event):
    user_id: int

class Model(pydantic.BaseModel):
    event: dynapydantic.Polymorphic[Event]

model = Model.model_validate({"event": {"type": "UserCreated", "user_id": 42}})
assert isinstance(model.event, UserCreated)
assert model.model_dump() == {
    "event": {"type": "UserCreated", "user_id": 42}
}

round_trip = Model.model_validate(model.model_dump())
assert isinstance(round_trip.event, UserCreated)
```

### Plugin discovery

`SubclassTrackingModel` can discover models provided by separately installed
packages through Python entry points. Give the base model an entry-point group,
load the plugins before defining the polymorphic field, and each plugin can
register subclasses without the base package importing them directly:

```python
# base_package/models.py
import dynapydantic

class Animal(
    dynapydantic.SubclassTrackingModel,
    discriminator_field="type",
    plugin_entry_point="animal.plugins",
):
    pass
```

A plugin package declares the same group in its `pyproject.toml`. An entry
point may name a module (everything imported by that module is registered):

```toml
[project.entry-points."animal.plugins"]
cats-and-dogs = "animal_plugins"
```

```python
# animal_plugins/__init__.py
import typing as ty
from base_package.models import Animal

class Dog(Animal):
    type: ty.Literal["Dog"] = "Dog"
    bark_volume: int
```

The application loads the group before constructing its model schema:

```python
import dynapydantic
import pydantic
from base_package.models import Animal

dynapydantic.load_plugins(Animal)

class Model(pydantic.BaseModel):
    animal: dynapydantic.Polymorphic[Animal]

model = Model.model_validate({"animal": {"type": "Dog", "bark_volume": 100}})
assert model.animal.type == "Dog"
```

For plugins that need explicit registration or deferred imports, point the
entry point at a callable instead:

```toml
[project.entry-points."animal.plugins"]
more-animals = "animal_plugins.registration:register_models"
```

The callable is invoked when `load_plugins()` runs. Entry points are provided
by the plugin distributions, so installing a new plugin adds its models to
the runtime union without changing the base package.

## Motivation
Consider the following simple class setup:
```python
import pydantic

class Base(pydantic.BaseModel):
    pass

class A(Base):
    field: int

class B(Base):
    field: str

class Model(pydantic.BaseModel):
    val: Base
```
As expected, we can use `A`'s and `B`'s for `Model.val`:
```python
>>> m = Model(val=A(field=1))
>>> m
Model(val=A(field=1))
```
However, we quickly run into trouble when serializing and validating:
```python
>>> m.model_dump()
{'val': {}}
>>> m.model_dump(serialize_as_any=True)
{'val': {'field': 1}}
>>> Model.model_validate(m.model_dump(serialize_as_any=True))
Model(val=Base())
```

Pydantic provides a solution for serialization via `serialize_as_any` (and
its corresponding field annotation `SerializeAsAny`) and
`polymorphic_serialization`, but offers no native solution for the validation
half. Currently, the canonical way of doing this is to annotate the field as a
union of all subclasses. Often, a single field in the model is chosen as the
"discriminator" in a
[discriminated union](https://docs.pydantic.dev/latest/concepts/unions/#discriminated-unions).
The discriminated pattern is the most robust way to do this, as it eliminates
ambiguity between the union members. This library, `dynapydantic`, automates
this process.

Let's reframe the above problem with `dynapydantic`:
```python
import dynapydantic
import pydantic

class Base(
    dynapydantic.SubclassTrackingModel,
    discriminator_field="name",
    discriminator_value_generator=lambda t: t.__name__,
):
    pass

class A(Base):
    field: int

class B(Base):
    field: str

class Model(pydantic.BaseModel):
    val: dynapydantic.Polymorphic[Base]
```
Now, the same set of operations works as intended:
```python
>>> m = Model(val=A(field=1))
>>> m
Model(val=A(field=1, name='A'))
>>> m.model_dump()
{'val': {'field': 1, 'name': 'A'}}
>>> Model.model_validate(m.model_dump())
Model(val=A(field=1, name='A'))
```

## How it works

### `TrackingGroup`
The core entity in this library is the `dynapydantic.TrackingGroup`:
```python
import typing as ty

import dynapydantic
import pydantic

mygroup = dynapydantic.TrackingGroup(
    name="mygroup",
    discriminator_field="name"
)

@mygroup.register("A")
class A(pydantic.BaseModel):
    """A class to be tracked, will be tracked as "A"."""
    a: int

@mygroup.register()
class B(pydantic.BaseModel):
    """Another class, will be tracked as "B"."""
    name: ty.Literal["B"] = "B"
    a: int

class Model(pydantic.BaseModel):
    """A model that can have A or B"""
    field: mygroup.union()  # call after all subclasses have been registered

print(Model(field={"name": "A", "a": 4})) # field=A(a=4, name='A')
print(Model(field={"name": "B", "a": 5})) # field=B(name='B', a=5)
```

The `union()` method produces a [discriminated union](https://docs.pydantic.dev/latest/concepts/unions/#discriminated-unions)
of all registered `pydantic.BaseModel` subclasses. It also accepts an
`plain=True` keyword argument to produce a plain `UnionType` for use
in type annotations, but since this is a runtime-computed union, this will not
work with static type checkers. This union is based on a discriminator field,
which was configured by the `discriminator_field` argument to `TrackingGroup`.
The field can be created by hand, as was shown with `B`, or `dynapydantic`
will inject it for you, as was shown with `A`.

`TrackingGroup` has a few opt-in features to make it more powerful and easier to use:
1. `discriminator_value_generator`: This parameter is an optional callback
  function that is called with each class that gets registered and produces a
  default value for the discriminator field. This allows the user to call
  `register()` without a value for the discriminator. For example, passing:
  `lambda cls: cls.__name__` would use the name of the class as the
   discriminator value.
2. `plugin_entry_point`: This parameter indicates to `dynapydantic` that there
  might be models to be discovered in other packages. Packages are discovered
  by the Python entrypoint mechanism. See the [plugin discovery example](#plugin-discovery)
  above for the package declarations and loading code.

### `SubclassTrackingModel`
The most common use case of this pattern is to automatically register subclasses
of a given `pydantic.BaseModel`. This is supported via the use of
`dynapydantic.SubclassTrackingModel`. For example:
```python
import typing as ty

import dynapydantic
import pydantic

class Base(
    dynapydantic.SubclassTrackingModel,
    discriminator_field="name",
    discriminator_value_generator=lambda cls: cls.__name__,
):
    """Base model, will track its subclasses"""

    # The TrackingGroup can be specified here like model_config, or passed in
    # kwargs of the class declaration, just like how model_config works with
    # pydantic.BaseModel. If you do it like this, you have to give the tracking
    # group a name, whereas using kwargs will generate the name for you.
    # tracking_config: ty.ClassVar[dynapydantic.TrackingGroup] = dynapydantic.TrackingGroup(
    #     name="BaseSubclasses",
    #     discriminator_field="name",
    #     discriminator_value_generator=lambda cls: cls.__name__,
    # )


class Intermediate(Base, exclude_from_union=True):
    """Subclasses can opt out of being tracked"""

class Derived1(Intermediate):
    """Non-direct descendants are registered"""
    a: int

class Derived2(Intermediate):
    """You can override the value generator if desired"""
    name: ty.Literal["Custom"] = "Custom"
    a: int

print(Base.registered_subclasses())
# {'Derived1': <class '__main__.Derived1'>, 'Custom': <class '__main__.Derived2'>}

# if plugin_entry_point was specified, load plugin packages
# Base.load_plugins()

class Model(pydantic.BaseModel):
    """A model that can have any registered Base subclass"""
    field: dynapydantic.Polymorphic[Base]

print(Model(field={"name": "Derived1", "a": 4}))
# field=Derived1(a=4, name='Derived1')
print(Model(field={"name": "Custom", "a": 5}))
# field=Derived2(name='Custom', a=5)
```
It is important to note that the subclasses that are supported are those that
were defined *prior* to defining the model that uses `dynapydantic.Polymorphic`
(`Model` in the above example). If you declare additional subclasses afterwards,
you must call `.model_rebuild(force=True)` on the model that uses the subclass
union.

### Alternative union methods
!!! warning "Caution"

    `dynapydantic` does **NOT** test if your models have ambiguities in them.
    This is up to **YOU**.

    Non-discriminated unions should only be used when you can **PROVE** that all
    possible subclasses will parse unambiguously. If there is ambiguity in the
    models, you can get unexpected results. If plugins are used, it is highly
    discouraged to use anything besides discriminated unions.

While the default discriminated union is the recommended and most robust
approach, it does require a field in the model to act as the discriminator. If
the full list of union members is known to the author ahead of time and can be
proven to be unambiguous from a validation perspective, then the discriminator
field can be omitted and a
[`"smart"`](https://docs.pydantic.dev/latest/concepts/unions/#smart-mode) or
[`"left_to_right"`](https://docs.pydantic.dev/latest/concepts/unions/#left-to-right-mode)
union may be used. `TrackingGroup` and `SubclassTrackingModel` support these
modes as well via the `union_mode` argument:
```python
import dynapydantic
import pydantic

class Base(
    dynapydantic.SubclassTrackingModel,
    union_mode="smart",
):
    """dynapydantic.Polymorphic[Base] will be a "smart" A | B"""

class A(Base):
    a: int

class B(Base):
    b: int

class Model(pydantic.BaseModel):
    field: dynapydantic.Polymorphic[Base]

print(Model(field={"b": 5}))
# field=B(b=5)
```

### Union realization

Union realization determines when registered subclasses are collected into the
union used by Pydantic:

| Mode | API | Tradeoff |
| --- | --- | --- |
| Immediately | `dynapydantic.Union[T]` | Easiest to inspect, but most sensitive to declaration order |
| Model construction | `dynapydantic.Polymorphic[T]` (default) | Supports static schemas, but new subclasses may require `model_rebuild(force=True)` |
| Validation | `union_realization="validation"` | Most tolerant of registration order, but adds runtime overhead |

With `TrackingGroup`, the union is realized when `.union()` is called. With
`SubclassTrackingModel`, the mode can be configured on the base class or
overridden for an individual `Polymorphic` field. In all cases, subclasses
must be registered before the relevant realization point; validation-time mode
defers that point until validation.

See [Picking a union realization mode](union_realizations.md) for the
complete explanation, configuration examples, and guidance for recursive
models and plugin-based registration.

## Caveats and Limitations

While `dynapydantic` does enable polymorphic validation, it is important to note
that several limitations exist:

- Subclasses must be registered before union/schema realization, depending on
  the selected mode.
- New subclasses may require `model_rebuild(force=True)` to update a schema,
  unless validation-time union realization is used.
- Non-discriminated unions can be ambiguous.
- Discriminator values must be unique within a tracking group.
- Plugin discovery depends on Python entry points.
- Runtime-generated unions are not fully visible to static type checkers.


## Testing

`dynapydantic` currently supports Python >= 3.10 and Pydantic >=2.8. The
following combinations are verified via automated testing (defined in
`noxfile.py`):

<table>
  <thead>
    <tr>
      <th></th>
      <th></th>
      <th colspan="6">Pydantic</th>
    </tr>
    <tr>
      <th></th>
      <th></th>
      <th scope="col">2.8</th>
      <th scope="col">2.9</th>
      <th scope="col">2.10</th>
      <th scope="col">2.11</th>
      <th scope="col">2.12</th>
      <th scope="col">2.13</th>
    </tr>
  </thead>
  <tbody>
     <th rowspan="7">Python </th>
    <tr>
      <th scope="row">3.10</th>
      <td>✓</td><td>✓</td><td>✓</td><td>✓</td><td>✓</td><td>✓</td>
    </tr>
    <tr>
      <th scope="row">3.11</th>
      <td>✓</td><td>✓</td><td>✓</td><td>✓</td><td>✓</td><td>✓</td>
    </tr>
    <tr>
      <th scope="row">3.12</th>
      <td>✓</td><td>✓</td><td>✓</td><td>✓</td><td>✓</td><td>✓</td>
    </tr>
    <tr>
      <th scope="row">3.13</th>
      <td>✓</td><td>✓</td><td>✓</td><td>✓</td><td>✓</td><td>✓</td>
    </tr>
    <tr>
      <th scope="row">3.14</th>
      <td></td><td></td><td></td><td></td><td>✓</td><td>✓</td>
    </tr>
  </tbody>
</table>

Run every combination locally with:

```sh
uv run nox
```

To run one combination, for example Python 3.13 with Pydantic 2.13:

```sh
uv run nox -s test-3.13-2.13
```
