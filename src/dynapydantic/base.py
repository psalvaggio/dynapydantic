"""Base class for dynamic pydantic models"""

import typing as ty

import pydantic
import pydantic_core


def direct_children_of_base_in_mro(derived: type, base: type) -> list[type]:
    """Find all classes in derived's MRO that are direct subclasses of base.

    Parameters
    ----------
    derived : type
        The class whose MRO is being examined.
    base : type
        The base class to find direct subclasses of.

    Returns
    -------
    list[type]
        Classes in derived's MRO that are direct subclasses of base.
    """
    return [cls for cls in derived.__mro__ if cls is not base and base in cls.__bases__]


class DynamicBaseModel(pydantic.BaseModel):
    """
    Base class for dynamically registered Pydantic models.
    """

    def __init_subclass__(
        cls,
        *args,
        discriminator_field: str | None = None,
        exclude_from_union: bool | None = None,
        pluggy_hook: str | None = None,
        **kwargs,
    ):
        super().__init_subclass__(*args, **kwargs)

    @classmethod
    def __pydantic_init_subclass__(
        cls,
        *args,
        discriminator_field: str | None = None,
        exclude_from_union: bool | None = None,
        pluggy_hook: bool | None = None,
        **kwargs,
    ):
        if DynamicBaseModel in cls.__bases__:
            if discriminator_field is None:
                msg = (
                    "Direct children of DynamicBaseModel must pass discriminator_field"
                )
                raise RuntimeError(msg)
            if exclude_from_union is not None:
                msg = (
                    "exclude_from_union should not be set by direct children "
                    "of DynamicBaseModel"
                )
                raise RuntimeError(msg)
            cls.__SUBCLASSES__: ty.ClassVar[dict[str, type[cls]]] = {}
            cls.__DISCRIMINATOR__: ty.ClassVar[str] = discriminator_field

            if pluggy_hook:
                import pluggy

                cls.__HOOKSPEC__ = pluggy.HookspecMarker(pluggy_hook)

                class _DynapydanticSpec:
                    @cls.__HOOKSPEC__
                    def register_models() -> list[type[cls]]:
                        f"""Return a list of {cls.__name__} subclasses."""
                        pass
                cls.__HOOKSPEC_CLS__ = _DynapydanticSpec


                def _load_plugins():
                    import pluggy
                    pm = pluggy.PluginManager(pluggy_hook)
                    pm.add_hookspecs(cls.__HOOKSPEC_CLS__)
                    pm.load_setuptools_entrypoints(pluggy_hook)
                    for plugin in pm.get_plugins():
                        if hasattr(plugin, "register_models"):
                            for model_cls in plugin.register_models():
                                if issubclass(model_cls, DynamicBaseModel):
                                    model_cls.register(model_cls)
                cls.load_plugins = staticmethod(_load_plugins)

                cls.hookimpl: ty.ClassVar[pluggy.HookimplMarker] = \
                    pluggy.HookimplMarker(pluggy_hook)
            return

        if pluggy_hook is not None:
            msg = (
                "pluggy_hook can only be specified on direct subclasses of "
                "DynamicBaseModel"
            )
            raise RuntimeError(msg)
        if exclude_from_union:
            return

        supers = direct_children_of_base_in_mro(cls, DynamicBaseModel)
        for base in supers:
            disc = base.__DISCRIMINATOR__
            field = cls.model_fields.get(disc)
            if field is None:
                msg = (
                    f"{cls.__name__} is derived from {base.__name__}, "
                    "which is a DynamicBaseModel with discrimantor field "
                    f'"{disc}". Therefore, it must define a "{disc}" field. '
                    "If this model is not intended to be a tracked subclass "
                    "and included in the subclass union, pass "
                    "exclude_from_config=True."
                )
                raise RuntimeError(msg)
            value = field.default
            if value == pydantic_core.PydanticUndefined:
                msg = (
                    f"{cls.__name__}.{disc} had no default value, it must "
                    "have one which is unique among all subclasses."
                )
                raise RuntimeError(msg)

            if (other := base.__SUBCLASSES__.get(value)) is not None:
                msg = (
                    f'{cls.__name__}.{disc} is set to "{value}", which '
                    "is already in use by another subclass ({other})."
                )
                raise RuntimeError(msg)

            base.__SUBCLASSES__[value] = cls

    @classmethod
    def union(cls):
        if DynamicBaseModel not in cls.__bases__:
            msg = "union() can only be called on direct children of DynamicBaseModel"
            raise TypeError(msg)

        return ty.Annotated[
            ty.Union[
                tuple(
                    (
                        ty.Annotated[x, pydantic.Tag(v)]
                        for v, x in cls.__SUBCLASSES__.items()
                    )
                )
            ],
            pydantic.Field(discriminator=cls.__DISCRIMINATOR__),
        ]

    @classmethod
    def registered_subclasses(cls) -> dict[str, type]:
        if DynamicBaseModel not in cls.__bases__:
            msg = (
                "registered_subclasses() can only be called on direct children "
                "of DynamicBaseModel"
            )
            raise TypeError(msg)

        return cls.__SUBCLASSES__
