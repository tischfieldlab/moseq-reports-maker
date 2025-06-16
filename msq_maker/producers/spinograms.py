import glob
import logging
import os
import subprocess
from dataclasses import dataclass, field
from typing import List, Type

from ..util import get_cpu_count
from ..core import BaseProducer, BaseOptionalProducerArgs, PluginRegistry, MSQ


@dataclass
class SpinogramsConfig(BaseOptionalProducerArgs):
    """Configuration for the `spinogram` producer.

    This producer produces spinograms. For more specific information you can check the `moseq-spinogram` package.
    """
    max_examples: int = field(default=10, metadata={"doc": "Maximum number of examples to generate for each syllable."})
    processors: int = field(default=get_cpu_count() // 2, metadata={"doc": "Number of processors to use for parallel processing. Defaults to half the number of available CPU cores."})
    extra_args: List[str] = field(default_factory=list, metadata={"doc": "Additional command line arguments to pass to the `spinograms` command, each token as an item in the list (à la subprocess style)."})



@PluginRegistry.register("spinograms")
class SpinogramsProducer(BaseProducer[SpinogramsConfig]):

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
            "--processors",
            str(self.pconfig.processors),
        ]
        if self.mconfig.sort:
            spinogram_args.append("--sort")

        if self.pconfig.extra_args:
            spinogram_args.extend(self.pconfig.extra_args)

        subprocess.check_call(spinogram_args)

        msq.manifest["spinograms"] = out_name
