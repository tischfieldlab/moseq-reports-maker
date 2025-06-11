import json
import logging
import os
import subprocess
from dataclasses import dataclass, field
from typing import List, Tuple, Type, Union
from typing_extensions import Literal

import pandas as pd

from ..msq import MSQ
from .base import BaseProducer, BaseProducerArgs, PluginRegistry


@dataclass
class SyllableClipsConfig(BaseProducerArgs):
    """Configuration for the `syllable_clips` producer.

    This producer produces syllable clips, or syllable-locked videos in RGB, depth, IR, or composed.
    For more specific information you can check the `moseq-syllable-clips` package.
    """
    prepend: float = field(default=2.0, metadata={"doc": "Time (seconds) to prepend to the start of each syllable clip."})
    append: float = field(default=2.0, metadata={"doc": "Time (seconds) to append to the end of each syllable clip."})
    max_examples: int = field(default=10, metadata={"doc": "Maximum number of examples to show per syllable."})
    streams: List[str] = field(default_factory=list, metadata={"doc": "List of streams to include in the output. Available streams: depth, rgb, ir, composed, but may depend on the modalities used when acquiring the raw data."})
    rgb_crop: Union[Literal["none", "auto"], Tuple[int,int,int,int]] = field(default="auto", metadata={"doc": "Crop to apply to RGB clips. If 'none', no crop is applied. If 'auto', the crop is determined automatically based on the extracted data ROI (only works properly if depth and RGB are the same shape, typical for Kinect2 data). Otherwise, a tuple of (x1, y1, x2, y2) defining the crop region."})

    def __post_init__(self):
        if len(self.streams) == 0:
            self.streams.extend(["depth", "rgb", "composed"])

    def get_rgb_crop(self) -> str:
        if isinstance(self.rgb_crop, tuple):
            return ",".join(str(x) for x in self.rgb_crop)
        else:
            return self.rgb_crop


@PluginRegistry.register("syllable_clips")
class SyllableClipsProducer(BaseProducer[SyllableClipsConfig]):

    @classmethod
    def get_args_type(cls) -> Type[SyllableClipsConfig]:
        return SyllableClipsConfig

    def run(self, msq: MSQ):
        out_dir = os.path.join(msq.spool_path, "syllable_clips")
        os.makedirs(out_dir, exist_ok=True)
        basename = "syllable"
        logging.info("Creating syllable clips at {}\n".format(out_dir))
        syl_clip_args = [
            "syllable-clips",
            "corpus-multiple",
            self.mconfig.index,
            self.mconfig.model,
            "--dir",
            out_dir,
            "--name",
            basename,
            "--count",
            self.mconfig.count,
            "--streams",
            *self.pconfig.streams,
            "--append",
            str(self.pconfig.append),
            "--prepend",
            str(self.pconfig.prepend),
            "--raw-path",
            self.mconfig.raw_data_path,
            "--num-examples",
            str(self.pconfig.max_examples),
            "--crop-rgb",
            self.pconfig.get_rgb_crop(),
        ]
        if self.mconfig.manifest_path is not None:
            syl_clip_args.extend(["--manifest", self.mconfig.manifest_path, "--man-uuid-col", self.mconfig.manifest_uuid_column, "--man-session-id-col", self.mconfig.manifest_session_id_column])

        if self.mconfig.sort:
            syl_clip_args.append("--sort")

        subprocess.call(syl_clip_args)

        args_path = os.path.join(out_dir, "{}.args.json".format(basename))
        with open(args_path) as args_file:
            args_data = json.load(args_file)

        man_path = os.path.join(out_dir, "{}.sources.tsv".format(basename))
        man_df = pd.read_csv(man_path, sep="\t")
        man_df["base_name"] = man_df["base_name"].apply(lambda x: os.path.join(out_dir, x))
        out = {"args": args_data, "manifest": man_df.to_dict("records")}
        msq.manifest["syllable_clips"] = out
