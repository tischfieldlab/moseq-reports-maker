from dataclasses import dataclass
from typing import Type

from moseq2_viz.model.util import get_syllable_statistics, parse_model_results
from moseq2_viz.util import parse_index
import numpy as np
import pandas as pd

from ..util import get_max_states, get_syllable_id_mapping
from ..core import BaseProducer, BaseOptionalProducerArgs, PluginRegistry, MSQ


@dataclass
class UsageConfig(BaseOptionalProducerArgs):
    """Configuration for the `usage` producer.

    This has no additional parameters, as it simply writes the usage values.
    """
    pass

@PluginRegistry.register("usage")
class UsageProducer(BaseProducer[UsageConfig]):

    @classmethod
    def get_args_type(cls) -> Type[UsageConfig]:
        return UsageConfig

    def run(self, msq: MSQ):
        _, index_dict = parse_index(self.mconfig.index)
        model_dict = parse_model_results(self.mconfig.model, sort_labels_by_usage=False)
        max_syllable = get_max_states(model_dict)

        if "train_list" in model_dict.keys():
            label_uuids = model_dict["train_list"]
        else:
            label_uuids = model_dict["keys"]

        groups = [index_dict["files"][uuid]["group"] for uuid in label_uuids]
        syllable_mapping = get_syllable_id_mapping(self.mconfig.model)

        data = []
        for i, label_arr in enumerate(model_dict["labels"]):
            tmp_usages, _ = get_syllable_statistics(label_arr, count="usage", max_syllable=max_syllable)
            total_usage = np.sum(list(tmp_usages.values()))

            tmp_frames, _ = get_syllable_statistics(label_arr, count="frames", max_syllable=max_syllable)
            total_frames = np.sum(list(tmp_frames.values()))

            for j, (usage, frames) in enumerate(zip(tmp_usages.values(), tmp_frames.values())):
                syllable = syllable_mapping[j]

                if syllable['usage'] > self.mconfig.max_syl:
                    continue

                data.append({
                    "id_raw": syllable["raw"],
                    "id_usage": syllable["usage"],
                    "id_frames": syllable["frames"],
                    "usage_usage": usage / total_usage,
                    "usage_frames": frames / total_frames,
                    "uuid": label_uuids[i],
                    "group": groups[i],
                })

        df = pd.DataFrame(data)

        if groups:
            df = df.loc[df["group"].isin(groups)]

        dest = "usage.ms{}.json".format(self.mconfig.max_syl)
        msq.write_dataframe(dest, df)
        msq.manifest["usage"] = dest
