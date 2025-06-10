from dataclasses import dataclass
from typing import Type

from moseq2_viz.model.util import get_syllable_statistics, parse_model_results
from moseq2_viz.util import parse_index
import numpy as np
import pandas as pd

from ..util import get_syllable_id_mapping
from ..msq import MSQ
from .base import BaseProducer, BaseProducerArgs, PluginRegistry


@dataclass
class UsageConfig(BaseProducerArgs):
    pass

@PluginRegistry.register("usage")
class UsageProducer(BaseProducer[UsageConfig]):

    @classmethod
    def get_args_type(cls) -> Type[UsageConfig]:
        return UsageConfig

    def run(self, msq: MSQ):
        _, index_dict = parse_index(self.mconfig.index)
        model_dict = parse_model_results(self.mconfig.model, sort_labels_by_usage=False)

        if "train_list" in model_dict.keys():
            label_uuids = model_dict["train_list"]
        else:
            label_uuids = model_dict["keys"]

        groups = [index_dict["files"][uuid]["group"] for uuid in label_uuids]
        syllable_mapping = get_syllable_id_mapping(self.mconfig.model)
        syllable_mapping = sorted(syllable_mapping, key=lambda row: row["raw"])

        data = []
        for i, label_arr in enumerate(model_dict["labels"]):
            tmp_usages, _ = get_syllable_statistics(label_arr, count="usage", max_syllable=self.mconfig.max_syl)
            total_usage = np.sum(list(tmp_usages.values()))

            tmp_frames, _ = get_syllable_statistics(label_arr, count="frames", max_syllable=self.mconfig.max_syl)
            total_frames = np.sum(list(tmp_frames.values()))

            for s in range(self.mconfig.max_syl):
                matching_sylls = list(filter(lambda row: row["raw"] == s, syllable_mapping))
                if len(matching_sylls) == 0:
                    continue
                syll = matching_sylls[0]

                data.append({
                    "id_raw": syll["raw"],
                    "id_usage": syll["usage"],
                    "id_frames": syll["frames"],
                    "usage_usage": tmp_usages[s] / total_usage,
                    "usage_frames": tmp_frames[s] / total_frames,
                    "uuid": label_uuids[i],
                    "group": groups[i],
                })

        df = pd.DataFrame(data)

        if groups:
            df = df.loc[df["group"].isin(groups)]

        dest = "usage.ms{}.json".format(self.mconfig.max_syl)
        msq.write_dataframe(dest, df)
        msq.manifest["usage"] = dest
