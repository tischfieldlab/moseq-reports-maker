from dataclasses import dataclass, field
from typing import List, Type

from moseq2_viz.model.dist import get_behavioral_distance
from moseq2_viz.util import parse_index
import pandas as pd

from ..util import get_max_states, get_syllable_id_mapping, syllableMatricesToLongForm
from ..core import MSQ, BaseOptionalProducerArgs, BaseProducer, PluginRegistry


@dataclass
class BehavioralDistanceConfig(BaseOptionalProducerArgs):
    """Configuration for the `behavioral_distance` Producer.

    You should not need to modify this configuration.
    """
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
            max_syllable=get_max_states(self.mconfig.model),
            sort_labels_by_usage=False,
            count="usage",
            dist_options=dist_opts,
            distances=self.pconfig.distances,
        )

        syllable_mapping = get_syllable_id_mapping(self.mconfig.model)

        df_dict = syllableMatricesToLongForm(dist, syllable_mapping)

        df = pd.DataFrame.from_dict(data=df_dict)
        #df = df[df["id_usage"] <= self.mconfig.max_syl]
        dest = "behaveDistances.ms{}.json".format(self.mconfig.max_syl)
        msq.write_dataframe(dest, df)
        msq.manifest["behave_dist"] = dest
