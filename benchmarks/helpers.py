"""Model builders shared by the dynapydantic benchmarks

Every builder creates brand new classes so that benchmarks never share
tracking state (registering a model mutates the tracking group it belongs to).
"""

import typing as ty

import pydantic

import dynapydantic

BaseT: ty.TypeAlias = type[dynapydantic.SubclassTrackingModel]


def discriminated_base(union_realization: str = "model-construction") -> BaseT:
    """Create a fresh discriminated tracking base class

    Parameters
    ----------
    union_realization
        When the union should be realized, see `dynapydantic.UnionRealization`

    Returns
    -------
    type[dynapydantic.SubclassTrackingModel]
        The newly created base class
    """
    return pydantic.create_model(
        "Base",
        __base__=dynapydantic.SubclassTrackingModel,
        __cls_kwargs__={
            "discriminator_field": "type",
            "discriminator_value_generator": lambda cls: cls.__name__,
            "union_realization": union_realization,
        },
    )


def plain_base(union_mode: str = "smart") -> BaseT:
    """Create a fresh non-discriminated tracking base class

    Parameters
    ----------
    union_mode
        Either "smart" or "left_to_right"

    Returns
    -------
    type[dynapydantic.SubclassTrackingModel]
        The newly created base class
    """
    return pydantic.create_model(
        "Base",
        __base__=dynapydantic.SubclassTrackingModel,
        __cls_kwargs__={"union_mode": union_mode},
    )


def add_subclasses(base: BaseT, n_models: int) -> list[BaseT]:
    """Declare `n_models` tracked subclasses of `base`

    Each subclass carries a distinct required field so that the models stay
    distinguishable in non-discriminated unions as well.

    Parameters
    ----------
    base
        The tracking base class
    n_models
        Number of subclasses to declare

    Returns
    -------
    list[type[dynapydantic.SubclassTrackingModel]]
        The newly declared subclasses
    """
    models = []
    for i in range(n_models):
        fields: dict[str, ty.Any] = {
            f"field_{i}": (int, ...),
            "label": (str, ...),
            "ratio": (float, 0.0),
            "tags": (list[str], pydantic.Field(default_factory=list)),
        }
        models.append(pydantic.create_model(f"Model{i}", __base__=base, **fields))
    return models


def container_model(
    base: BaseT,
    union_realization: str | None = None,
) -> type[pydantic.BaseModel]:
    """Create a model holding a single polymorphic field

    Parameters
    ----------
    base
        The tracking base class used as the field annotation
    union_realization
        If given, overrides the union realization time of `base`

    Returns
    -------
    type[pydantic.BaseModel]
        The newly created container model
    """
    annotation = (
        dynapydantic.Polymorphic[base]
        if union_realization is None
        else dynapydantic.Polymorphic[base, union_realization]
    )
    return pydantic.create_model("Container", item=(annotation, ...))


def payloads(models: list[BaseT], *, discriminated: bool = True) -> list[dict]:
    """Build one validation payload per model

    Parameters
    ----------
    models
        The tracked models to build payloads for
    discriminated
        Whether the discriminator field should be included in the payload

    Returns
    -------
    list[dict]
        The payloads, wrapped in the container model's field
    """
    out = []
    for i, model in enumerate(models):
        payload = {
            f"field_{i}": i,
            "label": f"label-{i}",
            "ratio": i / 2,
            "tags": ["alpha", "beta"],
        }
        if discriminated:
            payload["type"] = model.__name__
        out.append({"item": payload})
    return out
