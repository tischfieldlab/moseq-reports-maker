from dataclasses import dataclass
from typing import Type

from moseq2_viz.util import parse_index
import pandas as pd

from ..core import BaseProducer, BaseProducerArgs, PluginRegistry, MSQ


@dataclass
class SampleManifestConfig(BaseProducerArgs):
    """Configuration for the `sample_manifest` producer.

    This has no additional parameters, as it simply writes the sample manifest.
    """
    pass


@PluginRegistry.register("sample_manifest")
class SampleManifestProducer(BaseProducer[SampleManifestConfig]):

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
