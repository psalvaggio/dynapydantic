"""Version checking utilities."""

import pytest

from dynapydantic.version_check import (
    pydantic_ge,
    pydantic_gt,
    pydantic_le,
    pydantic_lt,
)


def skipif_mark_pydantic_version(
    *,
    le: tuple[int, ...] | None = None,
    lt: tuple[int, ...] | None = None,
    ge: tuple[int, ...] | None = None,
    gt: tuple[int, ...] | None = None,
) -> pytest.MarkDecorator:
    """Return a pydantic.mark.skipif based on the pydantic version.

    Skips the test if ANY passed condition is true.
    """
    msg: str | None = None
    if le is not None and pydantic_le(le):
        msg = "Pydantic version was <= {'.'.join(str(x) for x in le)}"
    elif lt is not None and pydantic_lt(lt):
        msg = "Pydantic version was < {'.'.join(str(x) for x in lt)}"
    elif ge is not None and pydantic_ge(ge):
        msg = "Pydantic version was >= {'.'.join(str(x) for x in ge)}"
    elif gt is not None and pydantic_gt(gt):
        msg = "Pydantic version was > {'.'.join(str(x) for x in gt)}"

    return (
        pytest.mark.skip(msg)
        if msg is not None
        else pytest.mark.skipif(False, reason="N/A")
    )
