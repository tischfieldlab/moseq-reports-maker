from abc import ABC, ABCMeta, abstractmethod
from dataclasses import dataclass, field, MISSING
from typing import Dict, Generic, Type, TypeVar, cast


from msq_maker import config
import msq_maker.msq
from msq_maker.util import SelfDocumentingMixin

@dataclass
class BaseProducerArgs(SelfDocumentingMixin):
    enabled: bool = field(default=True, metadata={"doc": "Enable or disable this producer."})


TProducerArgs = TypeVar("TProducerArgs", bound=BaseProducerArgs)

class BaseProducer(ABC, Generic[TProducerArgs], metaclass=ABCMeta):
    def __init__(self, configuration: "config.MoseqReportsConfig"):
        self.config = configuration
        self.mconfig: "config.ModelConfig" = configuration.model
        self.pconfig: TProducerArgs = cast(
            TProducerArgs, configuration.producers.get(PluginRegistry.get_plugin_name(type(self)), BaseProducerArgs())
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
