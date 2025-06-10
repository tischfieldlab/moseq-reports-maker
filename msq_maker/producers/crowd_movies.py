import glob
import logging
import os
import subprocess
from dataclasses import dataclass, field
from typing import Tuple, Type, Union
from typing_extensions import Literal

import h5py
from moseq2_viz.util import parse_index
import numpy as np
import pandas as pd

from ..util import ensure_even
from ..msq import MSQ
from .base import BaseProducer, BaseProducerArgs, PluginRegistry


@dataclass
class CrowdMoviesConfig(BaseProducerArgs):
    raw_size: Union[Literal["auto"], Tuple[int, int]] = field(default="auto", metadata={"doc": "Size of the raw depth movie. If auto, will be estimated from the extraction metadata."})
    max_examples: int = field(default=40, metadata={"doc": "Maximum number of examples to show per syllable."})
    processes: Union[int, None] = field(default=None, metadata={"doc": "Number of processes to use for creating movies."})
    gaussfilter_space: Tuple[float, float] = field(default=(0,0), metadata={"doc": "x sigma and y sigma for Gaussian spatial filter to apply to data."})
    medfilter_space: int = field(default=0, metadata={"doc": "kernel size for median spatial filter."})
    min_height: int = field(default=5, metadata={"doc": "Minimum height for scaling videos."})
    max_height: int = field(default=80, metadata={"doc": "Maximum height for scaling videos."})
    cmap: str = field(default="jet", metadata={"doc": "Color map to use for depth movies."})

@PluginRegistry.register("crowd_movies")
class CrowdMoviesProducer(BaseProducer[CrowdMoviesConfig]):

    @classmethod
    def get_args_type(cls) -> Type[CrowdMoviesConfig]:
        return CrowdMoviesConfig

    def run(self, msq: MSQ):
        out_dir = os.path.join(self.config.msq.tmp_dir, "crowd_movies")
        os.makedirs(out_dir, exist_ok=True)

        # check if movies already exist
        if ((self.config.model.sort and self.config.model.count == "usage") or not self.config.model.sort) and len(
            glob.glob(os.path.join(out_dir, "*(usage)*.mp4"))
        ) > 0:
            logging.info("It appears crowd movies already exist. Skipping. \n")
            return
        elif (self.config.model.sort and self.config.model.count == "frames") and len(
            glob.glob(os.path.join(out_dir, "*(frames)*.mp4"))
        ) > 0:
            logging.info("It appears crowd movies already exist. Skipping. \n")
            return

        logging.info("Creating crowd movies at {}\n".format(out_dir))
        raw_size = self.estimate_crowd_movie_size()
        args = [
            "moseq2-viz",
            "make-crowd-movies",
            self.config.model.index,
            self.config.model.model,
            "--max-syllable",
            str(self.config.model.max_syl),
            "--output-dir",
            out_dir,
            "--sort",
            str(self.config.model.sort),
            "--count",
            self.config.model.count,
            "--raw-size",
            str(raw_size[0]),
            str(raw_size[1]),
            "--max-examples",
            str(self.pconfig.max_examples),
            "--gaussfilter-space",
            str(self.pconfig.gaussfilter_space[0]),
            str(self.pconfig.gaussfilter_space[1]),
            "--medfilter-space",
            str(self.pconfig.medfilter_space),
            "--min-height",
            str(self.pconfig.min_height),
            "--max-height",
            str(self.pconfig.max_height),
            "--cmap",
            self.pconfig.cmap,
            "--max-examples",
            str(self.pconfig.max_examples),
        ]
        if self.pconfig.processes is not None:
            args.extend(["--processes", str(self.pconfig.processes)])
        subprocess.call(args)
        logging.info("Completed creating crowd movies at {}\n".format(out_dir))

    def estimate_crowd_movie_size(self, padding=100):
        if self.pconfig.raw_size != "auto":
            return self.pconfig.raw_size
        else:
            _, sortedIndex = parse_index(self.mconfig.index)
            
            bounds = []
            for uuid in sortedIndex['files'].keys():
                h5_path = sortedIndex['files'][uuid]['path'][0]
                with h5py.File(h5_path, 'r') as h5:
                    mask = h5['/metadata/extraction/roi'][()]
                    mask_idx = np.nonzero(mask)
                    bounds.append({
                        'width': np.max(mask_idx[1]) - np.min(mask_idx[1]),
                        'height': np.max(mask_idx[0]) - np.min(mask_idx[0]),
                    })
            bounds = pd.DataFrame(bounds).median()
            return (ensure_even(int(bounds['width'] + padding)), ensure_even(int(bounds['height'] + padding)))
    
    
