from dataclasses import dataclass
from typing import Type

from joblib import Parallel, delayed
from moseq2_viz.util import parse_index
from moseq2_viz.model.trans_graph import get_transition_matrix
from moseq2_viz.model.util import parse_model_results
import pandas as pd

from ..util import get_max_states, get_syllable_id_mapping, syllableMatricesToLongForm
from ..core import BaseProducer, BaseOptionalProducerArgs, PluginRegistry, MSQ


@dataclass
class TransitionsConfig(BaseOptionalProducerArgs):
    """Configuration for the `transitions` producer.

    This has no additional parameters, as it simply writes the transition probability values.
    """
    pass


@PluginRegistry.register("transitions")
class TransitionsProducer(BaseProducer[TransitionsConfig]):

    @classmethod
    def get_args_type(cls) -> Type[TransitionsConfig]:
        return TransitionsConfig

    def run(self, msq: MSQ):
        _, sorted_index = parse_index(self.mconfig.index)
        model = parse_model_results(self.mconfig.model, sort_labels_by_usage=False, count="usage")
        max_syllable = get_max_states(model)
        syllable_mapping = get_syllable_id_mapping(self.mconfig.model)

        label_uuids = model["keys"]
        labels = model["labels"]

        trans_mats = {}
        trans_mats["raw"] = get_transition_matrix(labels, combine=False, normalize=None, max_syllable=max_syllable)

        transitions = Parallel(n_jobs=-1)(
            delayed(self._prepTransitionsForIndividual)(trans_mats, i, uuid, sorted_index, syllable_mapping) for i, uuid in enumerate(label_uuids)
        )

        df: pd.DataFrame = pd.concat(transitions, ignore_index=True)
        df = df[(df["row_id_usage"] < self.mconfig.max_syl) & (df["col_id_usage"] < self.mconfig.max_syl)]

        dest = "individual_transitions.ms{}.json".format(self.mconfig.max_syl)
        msq.write_dataframe(dest, df)
        msq.manifest["transitions"] = dest

    def _prepTransitionsForIndividual(self, trans_mats, idx, uuid, index, syllable_mapping):
        mats = {}
        for k, v in trans_mats.items():
            mats[k] = v[idx]

        decorate = {"uuid": uuid, "default_group": index["files"][uuid]["group"]}

        data = syllableMatricesToLongForm(mats, syllable_mapping, decorate)
        return pd.DataFrame.from_dict(data=data)