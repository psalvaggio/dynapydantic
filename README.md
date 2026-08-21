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

## Testing

The supported Python/Pydantic compatibility matrix is defined in `noxfile.py`:

| Python | Pydantic 2.8 | Pydantic 2.9 | Pydantic 2.10 | Pydantic 2.11 | Pydantic 2.12 | Pydantic 2.13 |
| ------ | :----------: | :----------: | :-----------: | :-----------: | :-----------: | :-----------: |
| 3.10   | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| 3.11   | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| 3.12   | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| 3.13   | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| 3.14   |   |   |   |   | ✓ | ✓ |

Run every combination locally with:

```sh
uv run nox
```

To run one combination, for example Python 3.13 with Pydantic 2.13:

```sh
uv run nox -s test-3.13-2.13
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
is to annotate the field as a union of all subclasses. Often, a single field
in the model is chosen as the "discriminator" in a
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
`plain=True` keyword argument to produce a plain `UnionType` for use
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
import typing as ty

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

### When are unions realized?

When using `TrackingModel` directly, there is only one option for when the union
is realized, which is the moment you call `.union()`. At this point, any classes
that have been registered will be present in the union. Registration of
additional classes after a call to `.union()` will not update the returned
union from a previous call, so it is important to consider order of operations.

When using `SubclassTrackingModel`, there are more options and each comes with
their own tradeoffs:

1. **Immediately**: When using `dynapydantic.Union[T]`, the union is realized
    immediately. This is the "most eager" option, but is also the most sensitive
    with order of operations. Type checkers will not understand this direct
    calls to `union()`, but `dynapydantic.Union[T]` will resolved to `T`.

    Despite the tradeoff on sensitivity to order of operations, this option can
    be desireable for applications that inspect field annotations directly.
    This normally arises in user-implemented model reflection code and with
    [`pydantic_settings`](https://pydantic.dev/docs/validation/latest/api/pydantic_settings/#_top).

2. **Model-construction time**: Instead of eagerly realizing the union in the
    field annotation, `dynapydantic.Polymorphic[T]` (in its default ),
    configuration will defer the union realization slightly, into the schema
    generation step for the model. The difference between this and option 1 is
    subtle, but does have an effect with recursive models. Consider the
    following:

    ```python
    import dynapydantic
    import pydantic

    class Base(dynapydantic.SubclassTrackingModel, union_mode="smart"):
        pass

    class A(Base, extra="forbid"):
        a: int

    class B(Base, extra="forbid"):
        other: dynapydantic.Polymorphic[Base]

    B(other={"other": {"other": {"a": 2}}}) # ValidationError (union only has A)

    B.model_rebuild(force=True)
    B(other={"other": {"other": {"a": 2}}}) # B(other=B(other=B(other=A(a=2))))
    ```
    if we used `Union[Base]`, the `model_rebuild()` call would do nothing, as
    the union had already been realized. To accomplish the same thing with
    eager unions, we would have to use a forward reference, like `"BUnion"` then
    call `dynapydantic.union(Base)` right before the `model_rebuild()` calls.

    Similar to `dynapydantic.Union`, `dyanpydantic.Polymorphic` is interpretable
    by the type checker, which will constrain fields to be of the base class
    type.

3. **Validation time**: Finally, realization of the union can be deferred to
    validation time. This makes the union construction process more robust to
    order of operations. In this formulation, all subclasses must be registered
    before the use of the union in validation, rather than the declaration of a
    model using the union field. This reduces the previous example down to:

    ```python
    import dynapydantic
    import pydantic

    class Base(
        dynapydantic.SubclassTrackingModel,
        union_mode="smart",
        union_realization="validation",
    ):
        pass

    class A(Base, extra="forbid"):
        a: int

    class B(Base, extra="forbid"):
        other: dynapydantic.Polymorphic[Base]

    B(other={"other": {"other": {"a": 2}}}) # B(other=B(other=B(other=A(a=2))))
    ```

    This option has the cleanest syntax, as not `model_rebuild()` calls are
    needed, but does incur a runtime penalty for potentially multiple schema
    compilations and the need for a field validator function, whereas options 1
    and 2 can produce static schema. When validating from JSON, the field
    validator receives data after Pydantic has decoded it. To preserve
    Pydantic's JSON-specific validation behavior (including strict validation),
    validation-time unions re-encode the field value before validating it with
    the realized adapter. This adds JSON encoding and decoding overhead on top
    of the normal validation cost. Like option 2, the field is able to be
    interpreted by type checkers as the base class.

As alluded to in the example for validation-time unions, this behavior can be
controlled via the model class declaration and the field annotation. Subclasses
of `SubclassTrackingModel` can pass a `union_realization` keyword argument with
the value of `"model-construction"` (default) or `"validation"` (or their
corresponding `UnionRealization` enum values) to control the default behavior of
when `dynapydantic.Polymorphic` will realize the union. This default can be
overriden at the `Polymorphic` call site by passing a second argument:
```python
class Model(pydantic.BaseModel):
    field: dynapydantic.Polymorphic[Base, "validation"]
```
