import os
from dataclasses import dataclass
from typing import Type

from moseq2_viz.scalars.util import scalars_to_dataframe
from moseq2_viz.util import parse_index

from ..msq import MSQ
from .base import BaseProducer, BaseProducerArgs, MoseqReportsConfig, PluginRegistry


@dataclass
class ScalarsConfig(BaseProducerArgs):
    pass


@PluginRegistry.register("scalars")
class ScalarsProducer(BaseProducer[ScalarsConfig]):
    def __init__(self, config: MoseqReportsConfig):
        super().__init__(config)

    @classmethod
    def get_args_type(cls) -> Type[ScalarsConfig]:
        return ScalarsConfig

    def run(self, msq: MSQ):
        _, sortedIndex = parse_index(self.mconfig.index)

        df = scalars_to_dataframe(sortedIndex, model_path=self.mconfig.model)

        # drop any scalars in units of px, keep only mm or other columns
        df = df.drop(columns=[c for c in df.columns.values.tolist() if c.endswith("_px")])

        if self.mconfig.groups:
            df = df.loc[df["group"].isin(self.mconfig.groups)]

        dests = {}
        for gname, gdata in df.groupby("labels (original)"):
            dest = os.path.join("scalars", "usage_scalars_{}.json".format(gname))
            dests[gname] = dest
            msq.write_dataframe(dest, gdata)
        msq.manifest["scalars"] = dests
