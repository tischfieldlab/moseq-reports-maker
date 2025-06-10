
from dataclasses import MISSING, Field, dataclass, field, asdict
import os
from typing import Dict, List

import toml

from msq_maker.producers.base import BaseProducerArgs, PluginRegistry
from msq_maker.util import get_groups_index





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
    manifest_uuid_column: str = "UUID"
    manifest_session_id_column: str = "Session_ID"

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
class MSQConfig:
    name: str = field(default="moseq-report", metadata={"doc": "Name of the report"})
    out_dir: str = field(default=os.getcwd(), metadata={"doc": "Output directory for the report"})
    tmp_dir: str = field(default=os.path.join(os.getcwd(), "tmp"), metadata={"doc": "Temporary directory for intermediate files"})
    ext: str = field(default="msq", metadata={"doc": "File extension for the final output file"})



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
                pklass = PluginRegistry.registry.get(producer_name)
                if pklass is None:
                    raise ValueError(f"Producer {producer_name} not found in registry.")
                msr_config.producers[producer_name] = pklass.get_args_type()(**v)
        return msr_config