# Picking a union realization mode

A "union realization" refers to the moment at which the members of a union are
decided. At realization time, the types that are being tracked in a
`TrackingGroup` are extracted from the internal mapping and produce a union for
use in a `pydantic` schema.

When using `TrackingGroup` directly, there is only one option for when the union
is realized, which is the moment you call `.union()`. At this point, any classes
that have been registered will be present in the union. Registration of
additional classes after a call to `.union()` will not update the returned
union from a previous call, so it is important to consider order of operations.

`SubclassTrackingModel`, is a bit more flexible in this regard. There are
currently three options for when a union may be realized, each with their own
tradeoffs:

1. **Immediately**: When using `dynapydantic.Union[T]`, the union is realized
    immediately. This is the "most eager" option, but is also the most sensitive
    with order of operations. Type checkers will not understand direct calls to
    `union()`, but `dynapydantic.Union[T]` will resolve to `T`.

    Despite the tradeoff on sensitivity to order of operations, this option can
    be desirable for applications that inspect field annotations directly. This
    normally arises in user-implemented model reflection code and with
    [`pydantic_settings`](https://pydantic.dev/docs/validation/latest/api/pydantic_settings/).

2. **Model-construction time**: Instead of eagerly realizing the union in the
    field annotation, `dynapydantic.Polymorphic[T]`, in its default
    configuration, will defer the union realization slightly, into the schema
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


    B(other={"other": {"other": {"a": 2}}})  # ValidationError (union only has A)

    B.model_rebuild(force=True)
    B(other={"other": {"other": {"a": 2}}})  # B(other=B(other=B(other=A(a=2))))
    ```
    if we used `Union[Base]`, the `model_rebuild()` call would do nothing, as
    the union had already been realized. To accomplish the same thing with
    eager unions, we would have to use a forward reference, like `"BUnion"` then
    call `dynapydantic.union(Base)` right before the `model_rebuild()` calls.

    Similar to `dynapydantic.Union`, `dynapydantic.Polymorphic` is interpretable
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


    B(other={"other": {"other": {"a": 2}}})  # B(other=B(other=B(other=A(a=2))))
    ```

    This option has the cleanest syntax, as no `model_rebuild()` calls are
    needed, but does incur a runtime penalty for potentially multiple schema
    compilations and the need for a field validator function, whereas options 1
    and 2 can produce static schema. When validating from JSON, the field
    validator receives data after Pydantic has decoded it. To preserve
    Pydantic's JSON-specific validation behavior (including strict validation),
    validation-time unions re-encode the field value before validating it with
    the realized adapter. This adds JSON encoding and decoding overhead on top
    of the normal validation cost.

    See the [benchmarks](benchmarks.md) for a full picture of how
    validation-time unions perform. They have a significant first-time
    validation penalty for building the schema and a consistent per-validation
    penalty for the validator-based schema rather than a static schema.

    Like option 2, the field is able to be interpreted by type checkers as the
    base class.

The union realization mode can be configured in the following ways:

1. Via a class keyword argument to define the default behavior for a base type:
    ```python
    import dynapydantic


    class Base(
        dynapydantic.SubclassTrackingModel,
        union_mode="smart",
        union_realization="validation",
    ):
        pass


    # subclass definitions...


    class Model(pydantic.BaseModel):
        field: dynapydantic.Polymorphic[Base]  # validation-time
    ```
2. Via a per-usage override via the `dynapydantic.Polymorphic` annotation:
    ```python
    import dynapydantic
    import pydantic


    class Base(
        dynapydantic.SubclassTrackingModel,
        union_mode="smart",
    ):
        pass


    # subclass definitions...


    class Model(pydantic.BaseModel):
        field: dynapydantic.Polymorphic[Base, "validation"]
    ```

The supported options are `"model-construction"` (default) or `"validation"`
(or their corresponding `UnionRealization` enum values).
