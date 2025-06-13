import moseq2_viz
import numpy as np
from sklearn.cluster import KMeans
from cytoolz import compose
from cytoolz.curried import get
from moseq2_viz.model.util import _gen_to_arr


def retrieve_pcs_from_slices_fixed(slices, pca_scores, max_dur=60, min_dur=3,
                             max_samples=100, npcs=10, subsampling=None,
                             remove_offset=False, **kwargs):
    """
    Subsample Principal components from syllable slices

    Args:
    slices (np.ndarray): syllable slices or subarrays
    pca_scores (np.ndarray): PC scores for respective session.
    max_dur (int): maximum syllable length.
    min_dur (int): minimum syllable length.
    max_samples (int): maximum number of samples to retrieve.
    npcs (int): number of pcs to use.
    subsampling (int): number of syllable subsamples (defined through KMeans clustering).
    remove_offset (bool): indicate whether to remove initial offset from each PC score.
    kwargs (dict): used to capture certain arguments in other parts of the codebase.

    Returns:
    syllable_matrix (np.ndarray): 3D matrix of subsampled PC projected syllable slices.
    """
    # pad using zeros, get dtw distances...

    # make function to filter syll durations
    filter_dur = compose(lambda dur: (dur < max_dur) & (dur > min_dur),
                         lambda inds: inds[1] - inds[0],
                         get(0))
    filtered_slices = _gen_to_arr(filter(filter_dur, slices))
    # select random samples
    if(len(filtered_slices) > 0):
        inds = np.random.randint(0, len(filtered_slices), size=max_samples)
        if not hasattr(inds, 'shape'):
            inds = [inds]
        use_slices = filtered_slices[inds]
    else:
        use_slices = []

    syllable_matrix = np.zeros((len(use_slices), max_dur, npcs), 'float32')

    for i, (idx, uuid, _) in enumerate(use_slices):
        syllable_matrix[i, :idx[1]-idx[0], :] = pca_scores[uuid][idx[0]:idx[1], :npcs]

    if remove_offset:
        syllable_matrix = syllable_matrix - syllable_matrix[:, 0, :][:, None, :]

    # get cluster averages - really good at selecting for different durations of a syllable
    if subsampling is not None and subsampling > 0:
        try:
            km = KMeans(subsampling)
            syllable_matrix = syllable_matrix.reshape(syllable_matrix.shape[0], max_dur * npcs)
            syllable_matrix = syllable_matrix[np.all(~np.isnan(syllable_matrix), axis=1), :]
            km.fit(syllable_matrix)
            syllable_matrix = km.cluster_centers_.reshape(subsampling, max_dur, npcs)
        except Exception:
            syllable_matrix = np.full((subsampling, max_dur, npcs), np.nan)

    return syllable_matrix

# Monkey patch the retrieve_pcs_from_slices function in moseq2_viz.model.util
# see https://github.com/dattalab/moseq2-viz/issues/130 for why this is necessary
moseq2_viz.model.util.retrieve_pcs_from_slices = retrieve_pcs_from_slices_fixed
