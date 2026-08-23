# dynapydantic

[![CI](https://github.com/psalvaggio/dynapydantic/actions/workflows/ci.yml/badge.svg)](https://github.com/psalvaggio/dynapydantic/actions/workflows/ci.yml)
[![Pre-commit](https://github.com/psalvaggio/dynapydantic/actions/workflows/pre-commit.yml/badge.svg)](https://github.com/psalvaggio/dynapydantic/actions/workflows/pre-commit.yml)
[![Docs](https://img.shields.io/badge/docs-Docs-blue?style=flat-square&logo=github&logoColor=white&link=https://psalvaggio.github.io/dynapydantic/latest/)](https://psalvaggio.github.io/dynapydantic/latest/)
[![PyPI - Version](https://img.shields.io/pypi/v/dynapydantic)](https://pypi.org/project/dynapydantic/)
[![Coverage Status](https://coveralls.io/repos/github/psalvaggio/dynapydantic/badge.svg?branch=main)](https://coveralls.io/github/psalvaggio/dynapydantic?branch=main)
[![Conda Version](https://img.shields.io/conda/v/conda-forge/dynapydantic)](https://anaconda.org/conda-forge/dynapydantic)

Runtime polymorphic validation and serialization for
[Pydantic](https://pydantic.dev) models, with automatic subclass discovery and
optional plugin support. Define a base model once, discover its subclasses
automatically, and validate/serialize them without maintaining a manual union.

## Quick start

The recommended setup is a discriminated `SubclassTrackingModel` with
`Polymorphic[T]`:

### Polymorphic models

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
Without `dynapydantic`, the annotation for `event` would need to be an explicit
union that must be updated each time a subclass is added.

## Why dynapydantic?

Pydantic can serialize subclasses with `serialize_as_any` and
`polymorphic_serialization`, but it does not provide a corresponding way to
validate arbitrary subclasses through a base model field. The usual solution is
an explicit union, which must be updated whenever a new model is added.
`SerializeAsAny` solves the serialization side of the problem, but not the
validation side: validating the serialized data through a base model produces
the base type rather than the concrete subclass. `dynapydantic` automates the
discriminated union needed for both operations while retaining Pydantic's
validation and serialization behavior.

| Approach | Limitation |
| --- | --- |
| Explicit union | Must be manually maintained |
| Base Pydantic model | Concrete types can be lost during validation and serialization |
| `SerializeAsAny` | Helps serialization, but not polymorphic validation |
| `dynapydantic` | Builds a runtime union, with optional plugin discovery |

A quick decision matrix for when to use this library:

| Use a regular union | Use `dynapydantic` |
| ------------------- | ------------------ |
| Types are fixed and local | Types are extension points |
| You control every type | Types are scattered or come from plugins |
| Static typing is the priority | Runtime discovery is required |

`dynapydantic` is most useful when the union becomes difficult or impossible to
maintain, such as when types are extension points, come from plugins, or an
explicit union would introduce a circular dependency.


## Installation and compatibility

The package declares support for Python >=3.10 and Pydantic >=2.8,<3. Pydantic
1 is not supported. The current CI matrix verifies compatibility up to the
currently-available upper bounds. Install via PyPI or conda:

```sh
pip install dynapydantic
conda install -c conda-forge dynapydantic
```

## Plugin discovery

`SubclassTrackingModel` can discover models provided by separately installed
packages through Python entry points. Give the base model an entry-point group,
load the plugins before defining the polymorphic field, and each plugin can
register subclasses without the base package importing them directly. Plugin
discovery happens in the application environment, so the plugin distribution
must be installed alongside the base package.

The base package and plugin package can be separate distributions:

```text
base-package/
  pyproject.toml
  base_package/models.py

animal-plugin/
  pyproject.toml
  animal_plugins/__init__.py
```

The plugin must be installed in the same environment as the application and
must depend on the package that defines the base model.

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

For reliable plugin discovery, use a discriminator-based union. Discriminator
values must be unique within a tracking group, and concrete subclasses should
normally declare the discriminator field with a `typing.Literal` value. The
discriminator value generator can inject that field when a subclass does not
declare it explicitly.

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

Discriminator values must be unique within a `TrackingGroup`. Discriminated
unions are the recommended default because they avoid ambiguity between
subclasses.

`TrackingGroup` has a few opt-in features to make it more powerful and easier to use:
1. `discriminator_value_generator`: This parameter is an optional callback
  function that is called with each class that gets registered and produces a
  default value for the discriminator field. This allows the user to call
  `register()` without a value for the discriminator. For example, passing:
  `lambda cls: cls.__name__` would use the name of the class as the
   discriminator value.
2. `plugin_entry_point`: This parameter indicates to `dynapydantic` that there
  might be models to be discovered in other packages. Packages are discovered
  by the Python entry point mechanism. See the [plugin discovery example](#plugin-discovery)
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

The usual application order is:

```text
define subclasses → load plugins → define the model using Polymorphic[T]
```

If subclasses are added after model declaration, rebuild the affected Pydantic
model. Alternatively, configure `union_realization="validation"` when the
registration order cannot be known in advance; this defers union construction
until validation and adds runtime overhead.

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
union used by Pydantic.

For most applications, use `dynapydantic.Polymorphic[T]` with the default
model-construction realization. Use validation-time realization when subclasses
may be registered after model declarations or when recursive or plugin-heavy
schemas require it.

| Mode | API | Tradeoff |
| --- | --- | --- |
| Immediate | `dynapydantic.Union[T]` | Easiest to inspect, but most sensitive to declaration order |
| Model construction | `dynapydantic.Polymorphic[T]` (default) | Supports static schemas, but new subclasses may require `model_rebuild(force=True)` |
| Validation | `union_realization="validation"` | Most tolerant of registration order, but adds runtime overhead |

With `TrackingGroup`, the union is realized when `.union()` is called. With
`SubclassTrackingModel`, the mode can be configured on the base class or
overridden for an individual `Polymorphic` field. In all cases, subclasses
must be registered before the relevant realization point; validation-time mode
defers that point until validation.

See [Picking a union realization mode](https://psalvaggio.github.io/dynapydantic/latest/union_realizations/)
for the complete explanation, configuration examples, and guidance for
recursive models and plugin-based registration.

## API at a glance

| API | Purpose |
| --- | --- |
| `SubclassTrackingModel` | Automatically tracks subclasses of a base model |
| `TrackingGroup` | Explicitly registers model types |
| `Polymorphic[T]` | Runtime-generated polymorphic annotation |
| `Union[T]` | Eagerly realized runtime union |
| `load_plugins(T)` | Loads entry-point plugins for a tracking group |
| `registered_models(T)` | Inspects registered subclasses |

See the [API reference](https://psalvaggio.github.io/dynapydantic/latest/reference/)
for signatures, configuration options, and exception types.

## Caveats and limitations

While `dynapydantic` does enable polymorphic validation, it is important to note
that several limitations exist:

- Subclasses must be registered before union/schema realization, depending on
  the selected mode.
- New subclasses may require `model_rebuild(force=True)` to update a schema,
  unless validation-time union realization is used.
- Non-discriminated unions can be ambiguous.
- Discriminator values must be unique within a tracking group.
- Plugin discovery depends on Python entry points.
- Runtime-generated unions are not fully visible to static type checkers. The
  field is generally typed as the base class, so use `isinstance()` or the
  discriminator value when narrowing to a concrete subclass.

Both normal and JSON Pydantic workflows are supported. For example, the
polymorphic field can be serialized with `model_dump_json()` and reconstructed
with `model_validate_json()`; the discriminator remains part of the serialized
data when using a discriminated union.


## Testing

The following Python and Pydantic combinations are verified via automated
testing (defined in
`noxfile.py`):

<table>
  <thead>
    <tr>
      <th></th>
      <th></th>
      <th colspan="6" style="text-align: center;">Pydantic</th>
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
     <th rowspan="7" style="text-align: center; vertical-align: middle;">
       Python
      </th>
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
