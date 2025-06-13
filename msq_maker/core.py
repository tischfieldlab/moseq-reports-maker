from abc import ABC, ABCMeta, abstractmethod
from dataclasses import MISSING, Field, dataclass, field, asdict
import json
import os
from typing import Any, Dict, Generic, List, Optional, Type, TypeVar, cast
import zipfile

import pandas as pd
import toml

from msq_maker.util import get_groups_index



class SelfDocumentingMixin:
    """Mixin to provide self-documenting capabilities for dataclasses."""

    @classmethod
    def document(cls, name: Optional[str] = None, indent: str = "  - ") -> str:
        """Generate a documentation string for the producer."""
        buffer = f"About the configuration for `{name if name is not None else cls.__name__}`\n\n"
        buffer += f"    {cls.__doc__}\n\n"

        if issubclass(cls, BaseOptionalProducerArgs):
            buffer += "This producer is optional. You can enable or disable it in the configuration file.\n\n"
        else:
            buffer += "This producer is mandatory. It will always be included in the report.\n\n"

        buffer += "Configuration Items:\n"
        if not hasattr(cls, "__dataclass_fields__"):
            buffer += f"{indent}No configuration items available.\n"
            return buffer

        else:

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

                if type_name == "str":
                    default_value = f"\"{default_value}\""

                buffer += f"{indent}{attr.name} ({type_name}): {attr.metadata.get('doc', '')} (default: {default_value})\n"
            return buffer


@dataclass
class ModelConfig(SelfDocumentingMixin):
    """Configuration for the model used in the report generation.

    You should updated the `index`, `model`, and `raw_data_path` fields to point to your model index file, model file, and raw data directory respectively.

    The `manifest_path` is optional and can be used to provide a mapping from extraction UUIDs to session IDs. It depends on the version of moseq2-extract that 
    you used to extract your raw data, specifically if it relies on the field `/metadata/extraction/parameters/input_file`.
    If this field is not set in your extracted h5 files, you should set the `manifest_path` to the path of a manifest file that contains a mapping from extraction UUIDs to session IDs.

    Set the groups field to specify which groups to include in the report. If left empty, all known groups will be used.

    You should not need to change the `sort`, `count`, and `max_syl` fields, as they are set to reasonable defaults.
    """
    index: str = field(default="", metadata={"doc": "Path to the model index file."})
    model: str = field(default="", metadata={"doc": "Path to the model file."})
    max_syl: int = field(default=100, metadata={"doc": "Maximum syllable ID to consider in the model."})
    sort: bool = field(default=True, metadata={"doc": "Whether to sort the syllables by usage in the model. Please leave this as True."})
    count: str = field(default="usage", metadata={"doc": "Count type to use for syllables. Options: 'usage', 'frames', 'raw'. Default is 'usage', please leave this as 'usage'."})
    groups: List[str] = field(default_factory=lambda: [], metadata={"doc": "List of groups to include in the report. If empty, all known groups will be used."})
    raw_data_path: str = field(default="", metadata={"doc": "Path to the raw data directory containing sessions. If empty, syllable-clips will not work correctly."})
    manifest_path: str = field(default="", metadata={"doc": "Path to the manifest file, containing a mapping from extraction UUID to session ID (i.e. `session_*`). If empty, the manifest will not be used, but syllable-clips may have trouble locating sessions."})
    manifest_uuid_column: str = field(default="UUID", metadata={"doc": "Column name in the manifest file that contains the UUIDs of the extractions."})
    manifest_session_id_column: str = field(default="Session_ID", metadata={"doc": "Column name in the manifest file that contains the session IDs (i.e. `session_*`)."})

    def __post_init__(self) -> None:
        self.process_groups()

    def process_groups(self) -> None:
        """Process the groups to ensure they exist, are unique, and in the user preferred order."""
        if self.index is not None and self.index != "":
            known_groups = get_groups_index(self.index)
        else:
            known_groups = []

        if self.groups is None or len(self.groups) == 0:
            self.groups = known_groups

        self.groups = [g for g in self.groups if g in known_groups]



@dataclass
class MSQConfig(SelfDocumentingMixin):
    """Configuration controlling some aspects for the MSQ report file generation.
    
    You will likely only need to change the `name`, `out_dir`, and `tmp_dir` fields.
    When using `msq-maker generate-config`, the out_dir and tmp_dir will be set to the same directory where the config file is saved.
    If `--name` is specified during `msq-maker generate-config`, it will be used as the name of the report.
    """
    name: str = field(default="moseq-report", metadata={"doc": "Name of the report"})
    out_dir: str = field(default=os.getcwd(), metadata={"doc": "Output directory for the report"})
    tmp_dir: str = field(default=os.path.join(os.getcwd(), "tmp"), metadata={"doc": "Temporary directory for intermediate files"})
    ext: str = field(default="msq", metadata={"doc": "File extension for the final output file"})


@dataclass
class BaseProducerArgs(SelfDocumentingMixin):
    pass

@dataclass
class BaseOptionalProducerArgs(BaseProducerArgs):
    enabled: bool = field(default=True, metadata={"doc": "Enable or disable this producer."})


class MoseqReportsConfig:
    def __init__(self) -> None:
        self.msq: MSQConfig = MSQConfig()
        self.model: ModelConfig = ModelConfig()
        self.producers: Dict[str, BaseProducerArgs] = PluginRegistry.gather_configs()

    def to_dict(self) -> Dict[str, BaseProducerArgs]:
        configs = {"msq": self.msq, "model": self.model, **self.producers}
        return {k: asdict(v) for k, v in configs.items()}  # type: ignore[call-overload]

    def write_config(self, output_file: str) -> None:
        with open(output_file, "w") as f:
            toml.dump(self.to_dict(), f)  # type: ignore[call-overload]

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
                klass = PluginRegistry.registry.get(producer_name)
                if klass is None:
                    raise ValueError(f"Producer {producer_name} not found in registry.")
                msr_config.producers[producer_name] = klass.get_args_type()(**v)
        return msr_config


class MSQ:
    def __init__(self, config: MSQConfig):
        self.config = config
        self.manifest: Dict[str, Any] = {}

    @property
    def report_path(self) -> str:
        """Path to the final report file."""
        return os.path.join(self.config.out_dir, f"{self.config.name}.{self.config.ext}")

    @property
    def spool_path(self) -> str:
        return self.config.tmp_dir

    def prepare(self):
        # Prepare the MSQ report generation process
        pass

    def bundle(self):
        self._write_manifest()
        # Finalize the MSQ report generation process
        zip = zipfile.ZipFile(self.report_path, "w", zipfile.ZIP_DEFLATED)

        for root, _, files in os.walk(self.spool_path):
            for file in files:
                arcname = os.path.join(os.path.relpath(root, self.spool_path), file)
                zip.write(os.path.join(root, file), arcname=arcname)
        zip.close()

    def write_dataframe(self, name: str, data: pd.DataFrame):
        # Write the data to a DataFrame
        dest = os.path.join(self.spool_path, name)
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        data.to_json(dest, orient="split")

    def write_unstructured(self, name: str, data: Any):
        # Write unstructured data to a file
        dest = os.path.join(self.spool_path, name)
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        with open(dest, "w") as f:
            json.dump(data, f, indent=4)

    def _write_manifest(self):
        # Write the manifest file
        manifest_path = os.path.join(self.spool_path, "manifest.json")
        with open(manifest_path, "w") as f:
            json.dump(self.manifest, f, indent=4)




TProducerArgs = TypeVar("TProducerArgs", bound=BaseProducerArgs)

class BaseProducer(ABC, Generic[TProducerArgs], metaclass=ABCMeta):
    def __init__(self, configuration: MoseqReportsConfig):
        self.config = configuration
        self.mconfig: ModelConfig = configuration.model
        self.pconfig: TProducerArgs = cast(
            TProducerArgs, configuration.producers.get(PluginRegistry.get_plugin_name(type(self)), BaseProducerArgs())
        )

    @classmethod
    def is_optional(cls) -> bool:
        """Check if the producer is optional."""
        return issubclass(cls.get_args_type(), BaseOptionalProducerArgs)

    @classmethod
    @abstractmethod
    def get_args_type(cls) -> Type[TProducerArgs]:
        ...

    @abstractmethod
    def run(self, msq: MSQ) -> None:
        pass


class PluginRegistryMetaclass(type):

    def __len__(self):
        return len(self.registry)


class PluginRegistry(metaclass=PluginRegistryMetaclass):
    registry: Dict[str, Type[BaseProducer]] = {}

    @classmethod
    def registered(cls) -> List[str]:
        """Get a list of all registered plugin names."""
        return list(cls.registry.keys())

    @classmethod
    def registered_optional(cls) -> List[str]:
        """Get a list of all registered optional plugin names."""
        return [name for name, klass in cls.registry.items() if klass.is_optional()]

    @classmethod
    def get(cls, plugin_name: str) -> Type[BaseProducer]:
        """Get a registered plugin class by its name."""
        return cls.registry[plugin_name]

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


