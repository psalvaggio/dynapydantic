import pluggy

from .hookspecs import DynapydanticSpec
from .base import DynamicBaseModel

def load_plugins():
    pm = pluggy.PluginManager("dynapydantic")
    pm.add_hookspecs(DynapydanticSpec)
    pm.load_setuptools_entrypoints("dynapydantic.plugins")
    for plugin in pm.get_plugins():
        if hasattr(plugin, "register_models"):
            for model_cls in plugin.register_models():
                if issubclass(model_cls, DynamicBaseModel):
                    model_cls.register(model_cls)
