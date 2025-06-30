import logging
import os
from typing import List, Optional
from moseq2_viz.model.util import parse_model_results
from moseq2_viz.util import parse_index
import pandas as pd

from msq_maker.core import ModelConfig
from msq_maker.util import get_groups_index, get_max_syllable

def parse_manifest(manifest_file: str) -> pd.DataFrame:
    """Parses the manifest file into a DataFrame.

    Args:
        manifest_file (str): The path to the manifest file.

    Returns:
        pd.DataFrame: The parsed manifest DataFrame.
    """
    ext = os.path.splitext(manifest_file)[1]

    df: pd.DataFrame
    if ext == ".tsv":
        df = pd.read_csv(manifest_file, sep="\t")
    elif ext == ".csv":
        df = pd.read_csv(manifest_file)
    elif ext == ".xlsx":
        df = pd.read_excel(manifest_file)
    else:
        raise ValueError(
            f'Did not understand manifest format. Supported file extensions are *.tsv (tab-separated), *.csv (comma-separated), or *.xlsx (Excel), but got "{ext}"'
        )

    return df


def get_model_config(model_file: Optional[str], index_file: Optional[str], manifest_file: Optional[str], raw_dir: Optional[str], groups: Optional[List[str]]) -> ModelConfig:
    """Retrieves the model configuration for a given model name.

    Args:
        model_file (str): The path to the model file.
        index_file (str): The path to the index file.

    Returns:
        ModelConfig: The configuration object for the specified model.
    """
    config = ModelConfig()

    if model_file is not None:
        config.model = os.path.abspath(model_file)
        model = parse_model_results(config.model, sort_labels_by_usage=True)
        config.max_syl = get_max_syllable(model)
    else:
        logging.warning("No model file provided, you are responsible for setting the following fields in the [model] section of the configuration:")
        logging.warning(" - model: Path to the model file")
        logging.warning(" - max_syl: Maximum sorted syllable ID that has emissions > 0")


    if index_file is not None:
        config.index = os.path.abspath(index_file)
        index, _ = parse_index(config.index)
        available_groups = get_groups_index(config.index)
        if groups is not None:
            logging.info("Groups were supplied")
            actual_groups = []
            for g in groups:
                if g not in available_groups:
                    logging.warning(f"  - Omitting group \"{g}\" because it was not found in the index!")
                    continue
                actual_groups.append(g)
            diff = set(available_groups) - set(actual_groups)
            if len(diff) > 0:
                logging.warning(f"The following groups from the index were excluded because the user omitted them:")
                for g in diff:
                    logging.warning(f"  - {g}")
            config.groups = [g for g in groups if g in available_groups]
        else:
            config.groups = available_groups
    else:
        logging.warning("No index file provided, you are responsible for setting the following fields in the [model] section of the configuration:")
        logging.warning(" - index: Path to the index file")
        logging.warning(" - groups: List of groups in the index")

    if raw_dir is not None:
        config.raw_data_path = os.path.abspath(raw_dir)
    else:
        logging.warning("No raw data directory provided, you are responsible for setting the following fields in the [model] section of the configuration:")
        logging.warning(" - raw_data_path: Path to the raw data directory containing sessions")


    if manifest_file is not None:
        config.manifest_path = os.path.abspath(manifest_file)
        manifest = parse_manifest(manifest_file)
        if config.manifest_uuid_column not in manifest.columns:
            logging.warning(f"Manifest does not contain the column \"{config.manifest_uuid_column}\", which shoudl contain the UUIDs of the recordings. You are responsible for setting the correct column in the [model] section of the configuration.")
        if config.manifest_session_id_column not in manifest.columns:
            logging.warning(f"Manifest does not contain the column \"{config.manifest_session_id_column}\", which should contain the session IDs of the recordings. You are responsible for setting the correct column in the [model] section of the configuration.")

    return config



