from abc import ABC, ABCMeta, abstractmethod
from dataclasses import dataclass, asdict, field, Field, MISSING
from typing import Dict, Generic, List, Type, TypeVar, cast


from msq_maker import config
import msq_maker.msq

@dataclass
class BaseProducerArgs:
    enabled: bool = field(default=True, metadata={"doc": "Enable or disable this producer."})

    @classmethod
    def document(cls, indent: str = "  - ") -> str:
        """Generate a documentation string for the producer."""
        buffer = ""
        for attr_name in cls.__dataclass_fields__.keys():
            attr: Field = cls.__dataclass_fields__[attr_name]
            type_name: str
            if isinstance(attr.type, type):
                type_name = attr.type.__name__
            else:
                type_name = str(attr.type).replace("typing.", "")

            # figure out the default value
            # if the field uses a default_factory, we call it to get the default value
            if attr.default is not MISSING and attr.default_factory is MISSING:
                default_value = attr.default
            elif attr.default is MISSING and attr.default_factory is not MISSING:
                default_value = attr.default_factory()
            else:
                default_value = None

            buffer += f"{indent}{attr.name} ({type_name}): {attr.metadata.get('doc', '')} (default: {default_value})\n"
        return buffer





TProducerArgs = TypeVar("TProducerArgs", bound=BaseProducerArgs)

class BaseProducer(ABC, Generic[TProducerArgs], metaclass=ABCMeta):
    def __init__(self, config: "config.MoseqReportsConfig"):
        self.config = config
        self.mconfig: "config.ModelConfig" = config.model
        self.pconfig: TProducerArgs = cast(
            TProducerArgs, config.producers.get(PluginRegistry.get_plugin_name(type(self)), BaseProducerArgs())
        )

    @classmethod
    @abstractmethod
    def get_args_type(cls) -> Type[TProducerArgs]:
        ...

    @abstractmethod
    def run(self, msq: msq_maker.msq.MSQ) -> None:
        pass


class PluginRegistry:
    registry: Dict[str, Type[BaseProducer]] = {}

    @classmethod
    def register(cls, plugin_name: str):
        """Decorator to register a plugin class."""

        def inner_wrapper(wrapped_class: Type[BaseProducer]) -> Type[BaseProducer]:
            cls.registry[plugin_name] = wrapped_class
            return wrapped_class

        return inner_wrapper

    @classmethod
    def get_plugin_name(cls, plugin_class: Type[BaseProducer]) -> str:
        """Get the plugin name from the class type."""
        for name, klass in cls.registry.items():
            if klass == plugin_class:
                return name
        raise ValueError(f"Plugin class {plugin_class} not found in registry.")

    @classmethod
    def gather_configs(cls) -> Dict[str, BaseProducerArgs]:
        """Gather the configuration for all registered plugins."""
        return {name: producer.get_args_type()() for name, producer in cls.registry.items()}
