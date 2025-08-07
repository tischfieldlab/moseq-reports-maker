import glob
import logging
import os
from dataclasses import dataclass, field
from typing import List, Tuple, Type, Union
from typing_extensions import Literal

import h5py
from moseq2_viz.util import parse_index
from moseq2_viz.helpers.wrappers import make_crowd_movies_wrapper
import numpy as np
import pandas as pd

from ..util import ensure_even, get_cpu_count
from ..core import BaseProducer, BaseOptionalProducerArgs, PluginRegistry, MSQ


@dataclass
class CrowdMoviesConfig(BaseOptionalProducerArgs):
    """Configuration for the `crowd_movies` producer, implemented by the moseq2-viz package."""
    raw_size: Union[Literal["auto"], Tuple[int, int]] = field(default="auto", metadata={"doc": "Size of the raw depth movie. If auto, will be estimated from the extraction metadata."})
    max_examples: int = field(default=40, metadata={"doc": "Maximum number of examples to show per syllable."})
    processes: Union[int, Literal["auto"]] = field(default="auto", metadata={"doc": "Number of processes to use for creating movies. If \"auto\", will use the number of available CPU cores (taking into account CPU affinity on systems that support it)."})
    gaussfilter_space: Tuple[float, float] = field(default=(0,0), metadata={"doc": "x sigma and y sigma for Gaussian spatial filter to apply to data."})
    medfilter_space: int = field(default=0, metadata={"doc": "kernel size for median spatial filter."})
    min_height: int = field(default=5, metadata={"doc": "Minimum height for scaling videos."})
    max_height: int = field(default=80, metadata={"doc": "Maximum height for scaling videos."})
    cmap: str = field(default="jet", metadata={"doc": "Color map to use for depth movies."})
    separate_by: Literal['default', 'groups', 'sessions', 'subjects'] = field(default='default', metadata={"doc": "Generate crowd movies by specified grouping."})
    specific_syllable: Union[int, None] = field(default=None, metadata={"doc": "Index of the specific syllable to render."})
    session_names: List[str] = field(default_factory=list, metadata={"doc": "Specific sessions to create crowd movies from."})
    scale: float = field(default=1.0, metadata={"doc": "Scaling from pixel units to mm."})
    max_dur: Union[int, None] = field(default=60, metadata={"doc": "Exclude syllables longer than this number of frames (None for no limit)."})
    min_dur: int = field(default=0, metadata={"doc": "Exclude syllables shorter than this number of frames."})
    legacy_jitter_fix: bool = field(default=False, metadata={"doc": "Set to true if you notice jitter in your crowd movies."})
    frame_path: str = field(default="frames", metadata={"doc": "Path to depth frames in h5 file."})
    progress_bar: bool = field(default=False, metadata={"doc": "Show verbose progress bars."})
    pad: int = field(default=30, metadata={"doc": "Pad crowd movie videos with this many frames."})
    seed: int = field(default=0, metadata={"doc": "Defines random seed for selecting syllable instances to plot."})


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
        crowd_movies_config = {
            "max_syllable": self.config.model.max_syl,
            "max_examples": self.pconfig.max_examples,
            "processes": self.pconfig.processes if self.pconfig.processes != "auto" else get_cpu_count(),
            "separate_by": self.pconfig.separate_by,
            "specific_syllable": self.pconfig.specific_syllable,
            "session_names": self.pconfig.session_names,
            "sort": self.config.model.sort,
            "count": self.config.model.count,
            "gaussfilter_space": self.pconfig.gaussfilter_space,
            "medfilter_space": self.pconfig.medfilter_space,
            "min_height": self.pconfig.min_height,
            "max_height": self.pconfig.max_height,
            "raw_size": raw_size,
            "scale": self.pconfig.scale,
            "cmap": self.pconfig.cmap,
            "max_dur": self.pconfig.max_dur,
            "min_dur": self.pconfig.min_dur,
            "legacy_jitter_fix": self.pconfig.legacy_jitter_fix,
            "frame_path": self.pconfig.frame_path,
            "progress_bar": self.pconfig.progress_bar,
            "pad": self.pconfig.pad,
            "seed": self.pconfig.seed,

        }

        make_crowd_movies_wrapper(
            self.config.model.index,
            self.config.model.model,
            out_dir,
            crowd_movies_config
        )

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
