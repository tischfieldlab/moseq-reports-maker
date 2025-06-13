from dataclasses import dataclass
from typing import Type

from ..core import BaseProducer, BaseProducerArgs, PluginRegistry, MSQ



@dataclass
class GroupsConfig(BaseProducerArgs):
    """Configuration for the `groups` producer.

    This has no additional parameters, as it simply writes the groups.
    """
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
