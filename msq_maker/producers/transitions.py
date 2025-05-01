from dataclasses import dataclass
from typing import Type

from joblib import Parallel, delayed
from moseq2_viz.util import parse_index
from moseq2_viz.model.trans_graph import get_transition_matrix
from moseq2_viz.model.util import parse_model_results

import pandas as pd

from msq_maker.util import get_syllable_id_mapping, syllableMatriciesToLongForm


from ..msq import MSQ
from .base import BaseProducer, BaseProducerArgs, MoseqReportsConfig
from .base import PluginRegistry


@dataclass
class TransitionsConfig(BaseProducerArgs):
    pass


@PluginRegistry.register("transitions")
class TransitionsProducer(BaseProducer[TransitionsConfig]):
    def __init__(self, config: MoseqReportsConfig):
        super().__init__(config)

    @classmethod
    def get_args_type(cls) -> Type[TransitionsConfig]:
        return TransitionsConfig

    def run(self, msq: MSQ):
        _, sorted_index = parse_index(self.mconfig.index)
        model = parse_model_results(self.mconfig.model, sort_labels_by_usage=False, count="usage")
        syllable_mapping = get_syllable_id_mapping(self.mconfig.model)

        label_uuids = model["keys"]
        labels = model["labels"]

        trans_mats = {}
        trans_mats["raw"] = get_transition_matrix(labels, combine=False, normalize=None, max_syllable=self.mconfig.max_syl)

        transitions = Parallel(n_jobs=-1)(
            delayed(self._prepTransitionsForIndividual)(trans_mats, i, uuid, sorted_index, syllable_mapping) for i, uuid in enumerate(label_uuids)
        )

        df = pd.concat(transitions, ignore_index=True)

        dest = "individual_transitions.ms{}.json".format(self.mconfig.max_syl)
        msq.write_dataframe(dest, df)
        msq.manifest["transitions"] = dest

    def _prepTransitionsForIndividual(self, trans_mats, idx, uuid, index, syllable_mapping):
        mats = {}
        for k, v in trans_mats.items():
            mats[k] = v[idx]

        decorate = {"uuid": uuid, "default_group": index["files"][uuid]["group"]}

        data = syllableMatriciesToLongForm(mats, syllable_mapping, decorate)
        return pd.DataFrame.from_dict(data=data)