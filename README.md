# dynapydantic

[![CI](https://github.com/psalvaggio/dynapydantic/actions/workflows/ci.yml/badge.svg)](https://github.com/psalvaggio/dynapydantic/actions/workflows/ci.yml)
[![Pre-commit](https://github.com/psalvaggio/dynapydantic/actions/workflows/pre-commit.yml/badge.svg)](https://github.com/psalvaggio/dynapydantic/actions/workflows/pre-commit.yml)
[![Docs](https://img.shields.io/badge/docs-Docs-blue?style=flat-square&logo=github&logoColor=white&link=https://psalvaggio.github.io/dynapydantic/dev/)](https://psalvaggio.github.io/dynapydantic/dev/)
[![PyPI - Version](https://img.shields.io/pypi/v/dynapydantic)](https://pypi.org/project/dynapydantic/)
[![Coverage Status](https://coveralls.io/repos/github/psalvaggio/dynapydantic/badge.svg?branch=main)](https://coveralls.io/github/psalvaggio/dynapydantic?branch=main)
[![Conda Version](https://img.shields.io/conda/v/conda-forge/dynapydantic)](https://anaconda.org/conda-forge/dynapydantic)


`dynapydantic` is an extension to the [pydantic](https://pydantic.dev) Python
package that allow for dynamic tracking of `pydantic.BaseModel` subclasses.

## Installation
This project can be installed via PyPI:
```
pip install dynapydantic
```
or with `conda` via the `conda-forge` channel:
```
conda install dynapydantic
```


## Motiviation
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
{'base': {}}
>>> m.model_dump(serialize_as_any=True)
{'val': {'field': 1}}
>>> Model.model_validate(m.model_dump(serialize_as_any=True))
Model(val=Base())
```

Pydantic provides a solution for serialization via `serialize_as_any` (and
its corresponding field annotation `SerializeAsAny`), but offers no native
solution for the validation half. Currently, the canonical way of doing this
is to annotate the field as a discriminated union of all subclasses. Often, a
single field in the model is chosen as the "discriminator". This library,
`dynapydantic`, automates this process.

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
Model(val=A(field=1, name='A')
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
`annotated=False` keyword argument to produce a plain `typing.Union` for use
in type annotations, but since this is a runtime-computed union, this will not
work with static type checkers. This union is based on a discriminator field,
which was configured by the `discriminator_field` argument to `TrackingGroup`.
The field can be created by hand, as was shown with `B`, or `dynapydantic`
will inject it for you, as was shown with `A`.

`TrackingGroup` has a few opt-in features to make it more powerful and easier to use:
1. `discriminator_value_generator`: This parameter is a optional callback
  function that is called with each class that gets registered and produces a
  default value for the discriminator field. This allows the user to call
  `register()` without a value for the discriminator. For example, passing:
  `lambda cls: cls.__name__` would use the name of the class as the
   discriminator value.
2. `plugin_entry_point`: This parameter indicates to `dynapydantic` that there
  might be models to be discovered in other packages. Packages are discovered
  by the Python entrypoint mechanism. See the `tests/example` directory for an
  example of how this works.

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

# if plugin_entry_point was specificed, load plugin packages
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
