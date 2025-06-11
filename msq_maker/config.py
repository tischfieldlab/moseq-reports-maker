
from dataclasses import dataclass, field, asdict
import os
from typing import Dict, List

import toml

from msq_maker.producers.base import BaseProducerArgs, PluginRegistry
from msq_maker.util import SelfDocumentingMixin, get_groups_index






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