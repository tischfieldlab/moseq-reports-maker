import glob
import logging
import os
import subprocess
from dataclasses import dataclass
import sys
from typing import Type

from ..msq import MSQ
from .base import BaseProducer, BaseProducerArgs, MoseqReportsConfig
from .base import PluginRegistry


@dataclass
class SpinogramsConfig(BaseProducerArgs):
    max_examples: int = 10


@PluginRegistry.register("spinograms")
class SpinogramsProducer(BaseProducer[SpinogramsConfig]):
    def __init__(self, config: MoseqReportsConfig):
        super().__init__(config)

    @classmethod
    def get_args_type(cls) -> Type[SpinogramsConfig]:
        return SpinogramsConfig

    def run(self, msq: MSQ):
        # check if spinograms already exist
        basename = "spinogram"
        out_name = f"{basename}.corpus-{'sorted' if self.mconfig.sort else 'unsorted'}-{self.mconfig.count}.json"
        if len(glob.glob(os.path.join(msq.spool_path, out_name))) > 0:
            logging.info("It appears spinograms already exist. Skipping. \n")
            return

        logging.info("Creating spinograms at {}\n".format(msq.spool_path))
        spinogram_args = [
            "spinogram",
            "plot-corpus",
            self.mconfig.index,
            self.mconfig.model,
            "--dir",
            msq.spool_path,
            "--save-data",
            "--no-plot",
            "--max-syllable",
            str(self.mconfig.max_syl),
            "--name",
            basename,
            "--count",
            self.mconfig.count,
            "--max-examples",
            str(self.pconfig.max_examples),
        ]
        if self.mconfig.sort:
            spinogram_args.append("--sort")
        subprocess.call(spinogram_args)

        msq.manifest["spinograms"] = out_name
