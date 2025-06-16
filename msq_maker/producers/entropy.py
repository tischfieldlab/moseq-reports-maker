from dataclasses import dataclass
from typing import Type

from moseq2_viz.util import parse_index
from moseq2_viz.info.util import entropy, entropy_rate
from moseq2_viz.model.util import parse_model_results
import pandas as pd


from ..core import BaseProducer, BaseOptionalProducerArgs, PluginRegistry, MSQ


@dataclass
class EntropyConfig(BaseOptionalProducerArgs):
    """Configuration for the `entropy` producer.

    This has no additional parameters, as it simply writes the entropy values.
    """
    pass


@PluginRegistry.register("entropy")
class EntropyProducer(BaseProducer[EntropyConfig]):

    @classmethod
    def get_args_type(cls) -> Type[EntropyConfig]:
        return EntropyConfig

    def run(self, msq: MSQ):
        _, sortedIndex = parse_index(self.mconfig.index)
        model_dict = parse_model_results(self.mconfig.model, sort_labels_by_usage=True, map_uuid_to_keys=True)

        common_params = {
            "truncate_syllable": self.config.model.max_syl,
            "relabel_by": None,
        }

        data = []
        for key in model_dict['labels'].kays():
            labels = model_dict['labels'][key]
            data.append({
                "uuid": key,
                "group": sortedIndex["files"][key]["group"],
                "entropy": entropy(labels, **common_params),
                "entropy_rate_bigram": entropy_rate(labels, normalize="bigram", **common_params),
                "entropy_rate_rows": entropy_rate(labels, normalize="rows", **common_params),
                "entropy_rate_columns": entropy_rate(labels, normalize="columns", **common_params),
            })

        df = pd.DataFrame(data)

        if self.mconfig.groups:
            df = df.loc[df["group"].isin(self.mconfig.groups)]

        dest = "entropy.json"
        msq.write_dataframe(dest, df)
        msq.manifest["entropy"] = dest
