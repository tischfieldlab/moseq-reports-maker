from dataclasses import dataclass, field
from typing import List, Type

from moseq2_viz.model.dist import get_behavioral_distance
from moseq2_viz.util import parse_index
import pandas as pd

from ..util import get_syllable_id_mapping, syllableMatricesToLongForm
from ..msq import MSQ
from .base import BaseProducer, BaseProducerArgs, PluginRegistry


@dataclass
class BehavioralDistanceConfig(BaseProducerArgs):
    distances: List[str] = field(default_factory=lambda: ["ar[init]", "ar[dtw]", "scalars", "pca[dtw]"], metadata={"doc": "List of distances to compute"})


@PluginRegistry.register("behavioral_distance")
class BehavioralDistanceProducer(BaseProducer[BehavioralDistanceConfig]):

    @classmethod
    def get_args_type(cls) -> Type[BehavioralDistanceConfig]:
        return BehavioralDistanceConfig

    def run(self, msq: MSQ):
        _, sorted_index = parse_index(self.mconfig.index)
        dist_opts = {"ar[dtw]": {"parallel": True}, "pca": {"parallel": True}}
        dist = get_behavioral_distance(
            sorted_index,
            self.mconfig.model,
            max_syllable=self.mconfig.max_syl,
            sort_labels_by_usage=False,
            count="usage",
            dist_options=dist_opts,
            distances=self.pconfig.distances,
        )

        syllable_mapping = get_syllable_id_mapping(self.mconfig.model)

        df_dict = syllableMatricesToLongForm(dist, syllable_mapping)

        df = pd.DataFrame.from_dict(data=df_dict)
        dest = "behaveDistances.ms{}.json".format(self.mconfig.max_syl)
        msq.write_dataframe(dest, df)
        msq.manifest["behavioral_distance"] = dest
