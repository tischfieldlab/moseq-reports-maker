from dataclasses import dataclass
from typing import Type

from moseq2_viz.util import parse_index
import pandas as pd

from ..msq import MSQ
from .base import BaseProducer, BaseProducerArgs, MoseqReportsConfig, PluginRegistry


@dataclass
class SampleManifestConfig(BaseProducerArgs):
    pass


@PluginRegistry.register("sample_manifest")
class SampleManifestProducer(BaseProducer[SampleManifestConfig]):
    def __init__(self, config: MoseqReportsConfig):
        super().__init__(config)

    @classmethod
    def get_args_type(cls) -> Type[SampleManifestConfig]:
        return SampleManifestConfig

    def run(self, msq: MSQ):
        _, index_dict = parse_index(self.mconfig.index)

        meta_keys = ["ApparatusName", "SessionName", "StartTime", "SubjectName"]

        data = []
        for uuid in index_dict["files"]:
            data.append({
                "uuid": uuid,
                "default_group": index_dict["files"][uuid]["group"],
                **{k: index_dict["files"][uuid]["metadata"].get(k, "") for k in meta_keys}
            })

        df = pd.DataFrame(data)
        dest = "samples.json"
        msq.write_dataframe(dest, df)
        msq.manifest["samples"] = dest
