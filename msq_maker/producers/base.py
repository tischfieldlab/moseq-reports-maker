from abc import ABC, ABCMeta, abstractmethod
from dataclasses import dataclass, asdict, field, Field
from typing import Dict, Generic, List, Type, TypeVar, cast
from moseq2_viz.util import parse_index

import toml

from msq_maker.msq import MSQ, MSQConfig


@dataclass
class BaseProducerArgs:
    enabled: bool = field(default=True, metadata={"doc": "Enable or disable this producer."})

    @classmethod
    def document(cls) -> str:
        """Generate a documentation string for the producer."""
        buffer = ""
        for attr_name in cls.__dataclass_fields__.keys():
            attr: Field = cls.__dataclass_fields__[attr_name]
            type_name: str
            if isinstance(attr.type, type):
                type_name = attr.type.__name__
            else:
                type_name = str(attr.type).replace("typing.", "")
            buffer += f"{attr.name} ({type_name}): {attr.metadata.get('doc', '')} (default: {attr.default})\n"
        return buffer


@dataclass
class ModelConfig:
    index: str = ""
    model: str = ""
    max_syl: int = 3
    sort: bool = True
    count: str = "usage"
    groups: List[str] = field(default_factory=lambda: [])
    raw_data_path: str = ""
    manifest_path: str = ""
    manifest_uuid_column: str = "uuid"
    manifest_session_id_column: str = "session_id"

    def __post_init__(self) -> None:
        self.process_groups()

    def process_groups(self) -> None:
        """Process the groups to ensure they exist, are unique, and in the user preferred order."""
        idx, _ = parse_index(self.index)
        known_groups = list(set([f["group"] for f in idx["files"]]))
        known_groups.sort()

        if self.groups is None or len(self.groups) == 0:
            self.groups = known_groups

        self.groups = [g for g in self.groups if g in known_groups]


class MoseqReportsConfig:
    def __init__(self) -> None:
        self.msq: MSQConfig = MSQConfig()
        self.model: ModelConfig = ModelConfig()
        self.producers: Dict[str, BaseProducerArgs] = PluginRegistry.gather_configs()

    def write_config(self, output_file: str) -> None:
        configs = {"msq": self.msq, "model": self.model, **self.producers}
        with open(output_file, "w") as f:
            toml.dump({k: asdict(v) for k, v in configs.items()}, f)  # type: ignore[call-overload]

    @classmethod
    def read_config(cls, config_file: str) -> "MoseqReportsConfig":
        """Read the configuration from a TOML file."""
        with open(config_file, "r") as f:
            config = toml.load(f)

        msr_config = cls()
        msr_config.msq = MSQConfig(**config.get("msq", {}))
        msr_config.model = ModelConfig(**config.get("model", {}))

        for k, v in config.items():
            producer_name = k.split(".")[1] if "." in k else k
            if producer_name not in ["msq", "model"]:
                pklass = PluginRegistry.registry.get(producer_name)
                if pklass is None:
                    raise ValueError(f"Producer {producer_name} not found in registry.")
                msr_config.producers[producer_name] = pklass.get_args_type()(**v)
        return msr_config


TProducerArgs = TypeVar("TProducerArgs", bound=BaseProducerArgs)


class BaseProducer(ABC, Generic[TProducerArgs], metaclass=ABCMeta):
    def __init__(self, config: MoseqReportsConfig):
        self.config = config
        self.mconfig: ModelConfig = config.model
        self.pconfig: TProducerArgs = cast(
            TProducerArgs, config.producers.get(PluginRegistry.get_plugin_name(type(self)), BaseProducerArgs())
        )

    @classmethod
    @abstractmethod
    def get_args_type(cls) -> Type[TProducerArgs]:
        ...

    @abstractmethod
    def run(self, msq: MSQ) -> None:
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
