import os
from dataclasses import dataclass
from typing import Type

import pandas as pd

from ..util import get_syllable_id_mapping
from ..msq import MSQ
from .base import BaseProducer, BaseProducerArgs, PluginRegistry


@dataclass
class LabelMapConfig(BaseProducerArgs):
    pass


@PluginRegistry.register("label_map")
class LabelMapProducer(BaseProducer[LabelMapConfig]):

    @classmethod
    def get_args_type(cls) -> Type[LabelMapConfig]:
        return LabelMapConfig

    def run(self, msq: MSQ):
        syllable_mapping = get_syllable_id_mapping(self.mconfig.model)
        sm_df = pd.DataFrame(syllable_mapping)
        dest = "label_map.json"
        sm_df.to_json(os.path.join(msq.spool_path, dest), orient="records")
        msq.manifest["label_map"] = dest
