import logging
import sys
from typing import Dict, Union
import psutil
from typing_extensions import TypedDict, Literal
from moseq2_viz.model.util import parse_model_results, relabel_by_usage, get_syllable_statistics
from moseq2_viz.util import parse_index


LabelMapping = TypedDict('LabelMapping', {
    'raw': int,
    'usage': int,
    'frames': int,
})
LabelMap = Dict[int, LabelMapping]
def get_syllable_id_mapping(model_file: str) -> LabelMap:
    '''Gets a mapping of syllable IDs.

    Parameters:
        model_file (str): path to a model to interrogate

    Returns:
        dict of dicts, indexed by raw id, with each sub-dict contains raw, usage, and frame ID assignments
    '''
    mdl = parse_model_results(model_file, sort_labels_by_usage=False)
    labels_usage = relabel_by_usage(mdl['labels'], count='usage')[1]
    labels_frames = relabel_by_usage(mdl['labels'], count='frames')[1]

    available_ids = list(set(labels_usage + labels_frames))
    label_map: LabelMap = {i: {'raw': i, 'usage': -1, 'frames': -1} for i in available_ids}
    label_map[-5] = {'raw': -5, 'usage': -5, 'frames': -5}  # -5 is the "unknown" label

    for usage_id, raw_id in enumerate(labels_usage):
        label_map[raw_id]['usage'] = usage_id

    for frames_id, raw_id in enumerate(labels_frames):
        label_map[raw_id]['frames'] = frames_id

    return label_map


def reindex_label_map(label_map: LabelMap, by: Literal['usage', 'frames', 'raw']) -> LabelMap:
    ''' Reindex a label map by usage, frames, or raw ID

    Parameters:
        label_map (LabelMap): The label map to reindex
        by (str): The key to reindex by, one of {'usage', 'frames', 'raw'}

    Returns:
        LabelMap: A new label map indexed by the specified key
    '''
    if by not in ['usage', 'frames', 'raw']:
        raise ValueError(f"Invalid index type '{by}'. Must be one of ['usage', 'frames', 'raw']")

    return {itm[by]: itm for itm in label_map.values()}


def get_max_syllable(model: dict) -> int:
    """Retrieves the maximum syllable from the model.
    
    Args:
        model (dict): a parsed model.
        
    Returns:
        int: The maximum syllable value.
    """
    syllable_stats = get_syllable_statistics(model["labels"])[0]
    for sid, use_count in syllable_stats.items():
        if use_count == 0:
            return sid
    return max(syllable_stats.keys(), default=100)


def get_groups_index(index_file: str) -> list:
    """Retrieves the groups from the index file.
    
    Args:
        index_file (str): The path to the index file.
        
    Returns:
        list: The groups in the index.
    """
    index, _ = parse_index(index_file)
    return list(sorted(set([f["group"] for f in index["files"]])))


def get_max_states(model: Union[str, dict]) -> int:
    ''' Gets the maximum number of states parameter from model training.
        This corresponds to the `--max-states` parameter from `moseq2-model learn-model` command.

        Parameters:
            model_file (str): path to the model file to interrogate
        
        Returns:
            int: max number of states parameter from model training
    '''
    if isinstance(model, str):
        model_dict = parse_model_results(model)
    elif isinstance(model, dict):
        model_dict = model
    else:
        raise ValueError("model must be a path to a model file or a parsed model dictionary")

    try:
        return model_dict['run_parameters']['max_states']
    except KeyError:
        return 100  # default value if not found in model


def syllableMatricesToLongForm(mats_dict, mapping: LabelMap, decorate=None):
    # assumes mats are indexed by RAW ID!!!

    shape = mats_dict[list(mats_dict.keys())[0]].shape
    data = []
    for i in range(shape[0]):
        i_map = mapping[i]

        for j in range(shape[1]):
            j_map = mapping[j]

            data.append({
                "row_id_raw": i_map["raw"],
                "row_id_usage": i_map["usage"],
                "row_id_frames": i_map["frames"],
                "col_id_raw": j_map["raw"],
                "col_id_usage": j_map["usage"],
                "col_id_frames": j_map["frames"],
                **(decorate if decorate is not None else {}),
                **{kind: mats_dict[kind][i, j] for kind in mats_dict.keys()}
            })

    return data

def ensure_even(num: int):
    """Ensure that number is even. If odd, add 1.
    
    Args:
        num (int): The number to check.

    Returns:
        int: The even number.
    """
    if (num % 2) == 1:
        return num + 1
    else:
        return num


def get_cpu_count() -> int:
    """Get the number of available CPUs cores.

    On systems that support CPU affinity, this will return the number of CPUs available to the current process.

    Returns:
        int: The number of CPUs, adjusted to be even.
    """
    if sys.platform == 'darwin':
        return psutil.cpu_count(logical=True)
    else:
        return len(psutil.Process().cpu_affinity())



logger: logging.Logger
def setup_logging() -> None:
    global logger
    logger = logging.getLogger(None)
    logger.handlers.clear()
    logger.setLevel(logging.INFO)

    # define a Handler which writes INFO messages or higher to the sys.stderr
    console = logging.StreamHandler()
    console.setLevel(logging.INFO)
    console_formatter = logging.Formatter("{levelname:8s} {message}", style="{")
    console.setFormatter(console_formatter)
    logger.addHandler(console)

def add_file_logging(log_file: str) -> None:
    # file handler
    handler = logging.FileHandler(log_file, mode="w")
    handler.setLevel(logging.INFO)
    file_formatter = logging.Formatter("{asctime} {levelname:8s} {message}", style="{")
    handler.setFormatter(file_formatter)
    logger.addHandler(handler)
