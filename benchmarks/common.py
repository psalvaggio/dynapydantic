"""Common utilities for benchmarks."""

import dataclasses
import enum
import json
import random
import typing as ty
import uuid

import pydantic

import dynapydantic


class Implementation(enum.Enum):
    """Implementations compared by the benchmarks."""

    DYNAPYDANTIC = "dyn"
    MANUAL = "man"


class UnionMode(enum.Enum):
    """Union modes exercised by the benchmarks."""

    DISCRIMINATED = "disc"
    SMART = "smart"


class DiscriminatorField(enum.Enum):
    """Discriminator field strategies exercised by the benchmarks."""

    INJECTED = "inject"
    EXPLICIT = "explicit"


class SubclassCount(int):
    """Integer parameter identifying the number of subclasses in a case."""


class PayloadCount(int):
    """Integer parameter identifying the number of payloads in a case."""


class PayloadFormat(enum.Enum):
    """Input formats exercised by the validation benchmarks."""

    PYTHON = "py"
    JSON = "json"

    def title(self) -> str:
        """Return the human-readable table heading for the format."""
        match self:
            case self.PYTHON:
                return "Python"
            case self.JSON:
                return "JSON"
        return "Unknown"


def idgen(arg: ty.Any) -> object | None:  # noqa: ANN401, PLR0911
    """Create a compact pytest parameter ID.

    Parameters
    ----------
    arg
        A benchmark parameter to encode.

    Returns
    -------
    object or None
        The encoded parameter ID, or ``arg`` when it has no custom encoding.
    """
    match arg:
        case Implementation():
            return f"impl={arg.value}"
        case UnionMode():
            return f"um={arg.value}"
        case dynapydantic.UnionRealization.MODEL_CONSTRUCTION:
            return "re=MC"
        case dynapydantic.UnionRealization.VALIDATION:
            return "re=VT"
        case DiscriminatorField():
            return f"df={arg.value}"
        case SubclassCount():
            return f"subcls_n={arg}"
        case PayloadCount():
            return f"payload_n={arg}"
        case PayloadFormat():
            return f"fmt={arg.value}"
        case None:
            return ""
    return arg


@dataclasses.dataclass(frozen=True)
class ParsedTestId:
    """A pytest test name and the parameters encoded by :func:`idgen`.

    Attributes
    ----------
    test_name
        The benchmark function name.
    implementation
        The implementation used by the benchmark case.
    union_mode
        The union mode used by the benchmark case.
    subclass_count
        The number of concrete subclasses in the generated hierarchy.
    realization
        When the union is realized by dynapydantic, the realization strategy.
    discriminator_field
        The discriminator field strategy, when applicable.
    payload_count
        The number of validation payloads, when applicable.
    payload_format
        The validation input format, when applicable.
    """

    test_name: str
    implementation: Implementation
    union_mode: UnionMode
    subclass_count: SubclassCount
    realization: dynapydantic.UnionRealization | None = None
    discriminator_field: DiscriminatorField | None = None
    payload_count: PayloadCount | None = None
    payload_format: PayloadFormat | None = None

    @classmethod
    def from_id(cls, test_id: str) -> ty.Self:
        """Parse a pytest ID generated from parameters formatted by :func:`idgen`.

        ``test_id`` may contain one or more hyphen-separated parameter fragments,
        for example ``"test_validation[impl=dyn-um=disc-subcls_n=10]"``.
        ``implementation``, ``union_mode``, and ``subclass_count`` are required;
        the remaining fields are optional because some benchmark cases do not
        use them.

        Parameters
        ----------
        test_id
            A pytest test name with its parameter ID in square brackets.

        Returns
        -------
        ParsedTestId
            The test name and decoded parameter values.

        Raises
        ------
        ValueError
            If the ID is malformed, contains an unknown parameter, or does not
            include a required field.
        """
        test_name, separator, encoded = test_id.rpartition("[")
        if not separator or not encoded.endswith("]") or not test_name:
            msg = f"Invalid pytest test ID: {test_id!r}"
            raise ValueError(msg)

        encoded = encoded[:-1]
        values: dict[str, object] = {}
        parsers: dict[str, ty.Callable[[str], object]] = {
            "impl": Implementation,
            "um": UnionMode,
            "re": _parse_union_realization,
            "df": DiscriminatorField,
            "subcls_n": SubclassCount,
            "payload_n": PayloadCount,
            "fmt": PayloadFormat,
        }
        if not encoded:
            msg = f"Missing parameters in pytest test ID: {test_id!r}"
            raise ValueError(msg)

        for fragment in encoded.split("-"):
            if fragment == "":
                continue
            key, separator, value = fragment.partition("=")
            if not separator or not value or key not in parsers:
                msg = f"Invalid parameter fragment: {fragment!r}"
                raise ValueError(msg)
            if key in values:
                msg = f"Duplicate parameter: {key!r}"
                raise ValueError(msg)
            try:
                values[key] = parsers[key](value)
            except ValueError as error:
                msg = f"Invalid value for parameter {key!r}: {value!r}"
                raise ValueError(msg) from error

        required = {"impl", "um", "subcls_n"}
        if missing := required - values.keys():
            msg = (
                f"Missing required parameter(s) in pytest test ID: {test_id!r}: "
                f"{', '.join(sorted(missing))}"
            )
            raise ValueError(msg)

        return cls(
            test_name=test_name,
            implementation=ty.cast("Implementation", values["impl"]),
            union_mode=ty.cast("UnionMode", values["um"]),
            subclass_count=ty.cast("SubclassCount", values["subcls_n"]),
            realization=ty.cast(
                "dynapydantic.UnionRealization | None", values.get("re")
            ),
            discriminator_field=ty.cast("DiscriminatorField | None", values.get("df")),
            payload_count=ty.cast("PayloadCount | None", values.get("payload_n")),
            payload_format=ty.cast("PayloadFormat | None", values.get("fmt")),
        )


def union_realization_label(val: dynapydantic.UnionRealization | None) -> str:
    """Return the short table label for a union realization.

    Parameters
    ----------
    val
        The union realization to label.

    Returns
    -------
    str
        ``"MC"`` for model-construction realization, ``"VT"`` for
        validation-time realization, or an empty string for ``None``.

    Raises
    ------
    ValueError
        If ``val`` is not a supported union realization.
    """
    match val:
        case dynapydantic.UnionRealization.MODEL_CONSTRUCTION:
            return "MC"
        case dynapydantic.UnionRealization.VALIDATION:
            return "VT"
        case None:
            return ""

    msg = f"Invalid union realization: {val}"
    raise ValueError(msg)


def _parse_union_realization(val: str) -> dynapydantic.UnionRealization:
    match val:
        case "MC":
            return dynapydantic.UnionRealization.MODEL_CONSTRUCTION
        case "VT":
            return dynapydantic.UnionRealization.VALIDATION
    msg = f"Invalid union realization: {val!r}"
    raise ValueError(msg)


def build_class_hierarchy(
    *,
    subclass_count: SubclassCount,
    implementation: Implementation,
    union_mode: UnionMode,
    realization: dynapydantic.UnionRealization = dynapydantic.UnionRealization.MODEL_CONSTRUCTION,  # noqa: E501
    inject: DiscriminatorField = DiscriminatorField.EXPLICIT,
) -> type[pydantic.BaseModel]:
    """Build a model containing a generated polymorphic class hierarchy.

    Parameters
    ----------
    subclass_count
        Number of concrete subclasses to generate.
    implementation
        Whether to use dynapydantic or the hand-rolled baseline.
    union_mode
        Union mode used by the generated hierarchy.
    realization
        Dynapydantic union realization strategy.
    inject
        Whether the discriminator field is injected or declared explicitly.

    Returns
    -------
    type[pydantic.BaseModel]
        A model whose ``field`` annotation contains the generated hierarchy.
    """
    if implementation == Implementation.MANUAL:
        ann = _build_manual_class_hierarchy(
            subclass_count=subclass_count, union_mode=union_mode
        )
    else:
        ann = _build_dyn_class_hierarchy(
            subclass_count=subclass_count,
            union_mode=union_mode,
            realization=realization,
            inject=inject,
        )

    class Model(pydantic.BaseModel):
        field: ann

    return Model


class Nested(pydantic.BaseModel, frozen=True, extra="forbid"):
    """Fixed leaf model shared by all benchmark hierarchies."""

    field1: int
    field2: str
    field3: float
    field4: str
    field5: bool


def _subclass_name(index: int) -> str:
    return f"Manual_{index}"


def _make_subclass(
    base: type[pydantic.BaseModel],
    module: str,
    subclass_name: str,
    **kwargs,
) -> type[pydantic.BaseModel]:
    return pydantic.create_model(
        subclass_name,
        __base__=base,
        __module__=module,
        __config__=pydantic.ConfigDict(frozen=True, extra="forbid"),
        number=(int, ...),
        text=(str, ...),
        score=(float, ...),
        nested=(Nested, ...),
        **kwargs,
    )


def _build_dyn_class_hierarchy(
    *,
    subclass_count: SubclassCount,
    union_mode: UnionMode,
    realization: dynapydantic.UnionRealization,
    inject: DiscriminatorField,
) -> ty.Any:  # noqa: ANN401
    module = f"dynapydantic_benchmark_{uuid.uuid4().hex}"

    if union_mode == UnionMode.DISCRIMINATED:
        if inject == DiscriminatorField.INJECTED:

            class Base(
                dynapydantic.SubclassTrackingModel,
                discriminator_field="name",
                discriminator_value_generator=lambda cls: cls.__name__,
                union_realization=realization,
            ):
                """Base class for the benchmark."""
        else:

            class Base(
                dynapydantic.SubclassTrackingModel,
                discriminator_field="name",
                union_realization=realization,
            ):
                """Base class for the benchmark."""
    else:

        class Base(
            dynapydantic.SubclassTrackingModel,
            union_mode="smart",
            union_realization=realization,
        ):
            """Base class for the benchmark."""

    if inject != DiscriminatorField.INJECTED:
        _ = [
            _make_subclass(
                Base,
                module,
                name,
                name=(
                    ty.Literal[name],  # type: ignore[not-a-type]
                    pydantic.Field(default=name),
                ),
            )
            for i in range(subclass_count)
            if (name := _subclass_name(i))
        ]
    else:
        _ = [
            _make_subclass(Base, module, _subclass_name(i))
            for i in range(subclass_count)
        ]

    return dynapydantic.Polymorphic[Base]


def _build_manual_class_hierarchy(
    *,
    subclass_count: SubclassCount,
    union_mode: UnionMode,
) -> ty.Any:  # noqa: ANN401
    module = f"dynapydantic_benchmark_{uuid.uuid4().hex}"

    class Base(pydantic.BaseModel):
        """Base class for the benchmark."""

    subclasses = [
        _make_subclass(
            Base,
            module,
            name,
            name=(
                ty.Literal[name],  # type: ignore[not-a-type]
                pydantic.Field(default=name),
            ),
        )
        for i in range(subclass_count)
        if (name := _subclass_name(i))
    ]

    union = ty.Union[tuple(subclasses)]  # noqa: UP007 # type: ignore[not-a-type]
    return (
        ty.Annotated[union, pydantic.Discriminator("name")]
        if union_mode == UnionMode.DISCRIMINATED
        else union
    )


RANDOM_SEED = 12345


def make_payloads(
    fmt: PayloadFormat, *, payload_count: PayloadCount, subclass_count: SubclassCount
) -> list[ty.Any]:
    """Generate deterministic payloads for a validation benchmark.

    Parameters
    ----------
    fmt
        Format in which to return each payload.
    payload_count
        Number of payloads to generate.
    subclass_count
        Number of subclasses represented by the generated hierarchy.

    Returns
    -------
    list of object
        Validation payloads in Python or JSON format.
    """
    # Select a deterministic interior member so lookup is not always biased
    # toward the first union branch, while keeping runs reproducible.
    rng = random.Random(RANDOM_SEED + subclass_count)  # noqa: S311
    base_payloads = [
        {
            "field": {
                "name": _subclass_name(i),
                "number": i,
                "text": f"hello {i}",
                "score": 1.23 * i,
                "nested": {
                    "field1": i,
                    "field2": f"hi {i}",
                    "field3": 2.34 * i,
                    "field4": f"bye {i}",
                    "field5": True,
                },
            }
        }
        for i in range(subclass_count)
    ]

    lower = max(1, subclass_count // 4)
    upper = min(subclass_count - 1, (subclass_count * 3) // 4)
    payloads = [base_payloads[rng.randint(lower, upper)] for i in range(payload_count)]

    if fmt == PayloadFormat.JSON:
        return [json.dumps(p) for p in payloads]
    return payloads
