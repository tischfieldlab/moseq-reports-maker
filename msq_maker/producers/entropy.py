from dataclasses import dataclass
from typing import Type

from moseq2_viz.util import parse_index
from moseq2_viz.model.util import parse_model_results, get_syllable_statistics, relabel_by_usage
from moseq2_viz.model.trans_graph import get_transition_matrix
import numpy as np
import pandas as pd

from msq_maker.util import get_syllable_id_mapping, reindex_label_map


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
        syllable_mapping = get_syllable_id_mapping(self.mconfig.model)
        syllable_mapping = reindex_label_map(syllable_mapping, by="usage")

        common_params = {
            "truncate_syllable": self.config.model.max_syl,
            "relabel_by": None, # labels are already relabeled by usage
        }

        # Calculate entropy and entropy_rate for each label set\
        # each yields a single value per label set
        entropy_data = []
        transition_entropy_data = []
        for key in model_dict['labels'].keys():
            labels = [np.array(model_dict['labels'][key])]

            # Calculate entropy and entropy rates
            entropy_data.append({
                "uuid": key,
                "group": sortedIndex["files"][key]["group"],
                "entropy": entropy(labels, **common_params)[0],
                "entropy_rate_bigram": entropy_rate(labels, normalize="bigram", **common_params)[0],
                "entropy_rate_rows": entropy_rate(labels, normalize="rows", **common_params)[0],
                "entropy_rate_columns": entropy_rate(labels, normalize="columns", **common_params)[0],
            })

            # Calculate transition entropy
            te_incoming = transition_entropy(labels, tm_smoothing=1, transition_type="incoming", **common_params)[0]
            te_outgoing = transition_entropy(labels, tm_smoothing=1, transition_type="outgoing", **common_params)[0]
            for i in range(self.mconfig.max_syl):
                s_map = syllable_mapping[i]
                transition_entropy_data.append({
                    "uuid": key,
                    "group": sortedIndex["files"][key]["group"],
                    "id_raw": s_map['raw'],
                    "id_frames": s_map['frames'],
                    "id_usage": s_map['usage'],
                    "trans_entropy_incoming": te_incoming[i],
                    "trans_entropy_outgoing": te_outgoing[i],
                })

        entropy_df = pd.DataFrame(entropy_data)
        transition_entropy_df = pd.DataFrame(transition_entropy_data)

        if self.mconfig.groups:
            entropy_df = entropy_df.loc[entropy_df["group"].isin(self.mconfig.groups)]
            transition_entropy_df = transition_entropy_df.loc[transition_entropy_df["group"].isin(self.mconfig.groups)]

        entropy_dest = "entropy.json"
        msq.write_dataframe(entropy_dest, entropy_df)
        msq.manifest["entropy"] = entropy_dest

        trans_entropy_dest = "transition_entropy.json"
        msq.write_dataframe(trans_entropy_dest, transition_entropy_df)
        msq.manifest["trans_entropy"] = trans_entropy_dest



###################################################################
#
# The following functions are copied from moseq2_viz.info.util
# But as of commit #cd8203d they are incorrectly implemented.
# Here we patch these functions to work correctly.
#
###################################################################

def entropy(labels, truncate_syllable=40, smoothing=1.0, relabel_by="usage"):
    """
    Compute syllable usage entropy, base 2.

    Args:
    labels (list of numpy.ndarray): list of predicted syllable label arrays from a group of sessions
    truncate_syllable (int): maximum number of relabeled syllable to keep for this calculation
    smoothing (float): a constant as pseudocount added to label usages before normalization
    relabel_by (str): mode to relabel predicted labels. Either 'usage', 'frames', or None.

    Returns:
    ent (list): list of entropies for each session.
    """

    if relabel_by is not None:
        labels, _ = relabel_by_usage(labels, count=relabel_by)

    ent = []
    for v in labels:
        usages = get_syllable_statistics([v])[0]

        syllables = np.array(list(usages.keys()))
        truncate_point = np.where(syllables == truncate_syllable)[0]

        if truncate_point is None or len(truncate_point) != 1:
            truncate_point = len(syllables)
        else:
            truncate_point = truncate_point[0]

        usages = np.array(list(usages.values()), dtype="float")
        usages = usages[:truncate_point] + smoothing
        usages /= usages.sum()

        ent.append(-np.sum(usages * np.log2(usages)))

    return ent


def entropy_rate(
    labels,
    truncate_syllable=40,
    normalize="row",
    smoothing=1.0,
    tm_smoothing=1.0,
    relabel_by="usage",
):
    """
    Compute entropy rate, base 2 using provided syllable labels. If syllable labels have not been re-labeled by usage, this function will do so.

    Args:
    labels (list or np.ndarray): a list of label arrays, where each entry in the list is an array of labels for one session.
    truncate_syllable (int): maximum number of labels to keep for this calculation.
    normalize (str): the type of transition matrix normalization to perform.
    smoothing (float): a constant as pseudocount added to label usages before normalization
    tm_smoothing (float): a constant as pseudocount added to label transition counts before normalization.
    relabel_by (str): how to re-order labels. Options are: 'usage', 'frames', or None.

    Returns:
    ent (list): list of entropy rates per syllable label
    """

    if relabel_by is not None:
        labels, _ = relabel_by_usage(labels, count=relabel_by)

    ent = []
    for v in labels:

        usages = get_syllable_statistics([v])[0]
        syllables = np.array(list(usages.keys()))
        truncate_point = np.where(syllables == truncate_syllable)[0]

        if truncate_point is None or len(truncate_point) != 1:
            truncate_point = len(syllables)
        else:
            truncate_point = truncate_point[0]

        syllables = syllables[:truncate_point]

        usages = np.array(list(usages.values()), dtype="float")
        usages = usages[:truncate_point] + smoothing
        usages /= usages.sum()

        tm = (
            get_transition_matrix(
                [v],
                max_syllable=100,
                normalize=None,
                smoothing=0,
                disable_output=True,
                combine=True,
            )
            + tm_smoothing
        )

        tm = tm[:truncate_point, :truncate_point]

        if normalize == "bigram":
            tm /= tm.sum()
        # http://reeves.ee.duke.edu/information_theory/lecture4-Entropy_Rates.pdf
        elif normalize == "rows":
            tm /= tm.sum(axis=1, keepdims=True)
        elif normalize == "columns":
            tm /= tm.sum(axis=0, keepdims=True)

        tm_safe = np.where(tm > 0, tm, 1)
        ent.append(-np.sum(usages[:, None] * tm * np.log2(tm_safe)))

    return ent


def transition_entropy(
    labels,
    tm_smoothing=0,
    truncate_syllable=40,
    transition_type="incoming",
    relabel_by="usage",
):
    """
    Compute directional syllable transition entropy. Based on whether the given transition_type is 'incoming' or or 'outgoing'.

    Args:
    labels (list or np.ndarray): a list of label arrays, where each entry in the list is an array of labels for one session.
    tm_smoothing (float): a constant as pseudocount added to label transition counts before normalization.
    truncate_syllable (int): maximum number of relabeled syllable to keep for this calculation
    transition_type (str): can be either "incoming" or "outgoing" to compute the entropy of each incoming or outgoing syllable transition.
    relabel_by (str): how to re-order labels. Options are: 'usage', 'frames', or None.

    Returns:
    entropies (list of np.ndarray): a list of transition entropies (either incoming or outgoing) for each session and syllable.
    """

    if transition_type not in ("incoming", "outgoing"):
        raise ValueError("transition_type must be incoming or outgoing")

    if relabel_by is not None:
        labels, _ = relabel_by_usage(labels, count=relabel_by)
    entropies = []

    for v in labels:
        usages = get_syllable_statistics([v])[0]

        syllables = np.array(list(usages))
        truncate_point = np.where(syllables == truncate_syllable)[0]

        if truncate_point is None or len(truncate_point) != 1:
            truncate_point = len(syllables)
        else:
            truncate_point = truncate_point[0]

        tm = (
            get_transition_matrix(
                [v],
                max_syllable=100,
                normalize=None,
                smoothing=0,
                combine=True,
                disable_output=True,
            )
            + tm_smoothing
        )
        tm = tm[:truncate_point, :truncate_point]

        if transition_type == "outgoing":
            # normalize each row (outgoing syllables)
            tm = tm.T
        # if incoming, don't reshape the transition matrix
        tm = tm / tm.sum(axis=0, keepdims=True)
        tm_safe = np.where(tm > 0, tm, 1)
        ent = -np.sum(tm * np.log2(tm_safe), axis=0)
        entropies.append(ent)

    return entropies
