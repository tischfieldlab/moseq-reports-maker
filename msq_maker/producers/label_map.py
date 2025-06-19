import os
from dataclasses import dataclass
from typing import Type

import pandas as pd

from ..util import get_syllable_id_mapping
from ..core import BaseProducer, BaseProducerArgs, PluginRegistry, MSQ


@dataclass
class LabelMapConfig(BaseProducerArgs):
    """Configuration for the `label_map` producer.

    This has no additional parameters, as it simply writes the label_map.
    """
    pass


@PluginRegistry.register("label_map")
class LabelMapProducer(BaseProducer[LabelMapConfig]):

    @classmethod
    def get_args_type(cls) -> Type[LabelMapConfig]:
        return LabelMapConfig

    def run(self, msq: MSQ):
        syllable_mapping = get_syllable_id_mapping(self.mconfig.model)
        sm_df = pd.DataFrame(syllable_mapping.values())
        sm_df = sm_df[sm_df["usage"] < self.mconfig.max_syl]
        dest = "label_map.json"
        sm_df.to_json(os.path.join(msq.spool_path, dest), orient="records")
        msq.manifest["label_map"] = dest
