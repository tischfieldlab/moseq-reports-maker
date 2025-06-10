from dataclasses import dataclass
from typing import Type

from ..msq import MSQ
from .base import BaseProducer, BaseProducerArgs, PluginRegistry



@dataclass
class GroupsConfig(BaseProducerArgs):
    pass


@PluginRegistry.register("groups")
class GroupsProducer(BaseProducer[GroupsConfig]):

    @classmethod
    def get_args_type(cls) -> Type[GroupsConfig]:
        return GroupsConfig

    def run(self, msq: MSQ):
        dest = "groups.json"
        msq.write_unstructured(dest, self.mconfig.groups)
        msq.manifest["groups"] = dest
