import logging
from typing import Dict, List, Optional
from typing_extensions import TypedDict
from moseq2_viz.model.util import parse_model_results, relabel_by_usage


LabelMap = TypedDict('LabelMap', {
    'raw': int,
    'usage': int,
    'frames': int,
})
def get_syllable_id_mapping(model_file: str) -> List[LabelMap]:
    ''' Gets a mapping of syllable IDs

    Parameters:
        model_file (str): path to a model to interrogate

    Returns:
        list of dicts, each dict contains raw, usage, and frame ID assignments
    '''
    mdl = parse_model_results(model_file, sort_labels_by_usage=False)
    labels_usage = relabel_by_usage(mdl['labels'], count='usage')[0]
    labels_frames = relabel_by_usage(mdl['labels'], count='frames')[0]

    label_map: Dict[int, LabelMap] = {}
    for si, sl in enumerate(mdl['labels']):
        for i, l in enumerate(sl):
            if l not in label_map:
                label_map[l] = {
                    'raw': l,
                    'usage': labels_usage[si][i],
                    'frames': labels_frames[si][i]
                }
    return list(label_map.values())


def get_max_states(model_file: str) -> int:
    ''' Gets the maximum number of states parameter from model training.
        This corresponds to the `--max-states` parameter from `moseq2-model learn-model` command.

        Parameters:
            model_file (str): path to the model file to interrogate
        
        Returns:
            int: max number of states parameter from model training
    '''
    model = parse_model_results(model_file)
    return model['run_parameters']['max_states']


def syllableMatricesToLongForm(mats_dict, mapping: List[LabelMap], decorate=None):
    # assumes mats are indexed by RAW ID!!!

    shape = mats_dict[list(mats_dict.keys())[0]].shape
    data = []
    for i in range(shape[0]):
        i_matching = list(filter(lambda row: row["raw"] == i, mapping))
        if len(i_matching) == 0:
            continue
        i_map = i_matching[0]

        for j in range(shape[1]):
            j_matching = list(filter(lambda row: row["raw"] == j, mapping))
            if len(j_matching) == 0:
                continue
            j_map = j_matching[0]

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


def setup_logging(log_file: Optional[str] = None) -> None:
    logging.captureWarnings(True)

    logger = logging.getLogger(None)
    logger.handlers.clear()
    logger.setLevel(logging.INFO)

    # define a Handler which writes INFO messages or higher to the sys.stderr
    console = logging.StreamHandler()
    console.setLevel(logging.INFO)
    console_formatter = logging.Formatter("{levelname:8s} {message}", style="{")
    console.setFormatter(console_formatter)
    logger.addHandler(console)

    # file handler
    if log_file is not None:
        handler = logging.FileHandler(log_file, mode="w")
        handler.setLevel(logging.INFO)
        file_formatter = logging.Formatter("{asctime} {levelname:8s} {message}", style="{")
        handler.setFormatter(file_formatter)
        logger.addHandler(handler)
