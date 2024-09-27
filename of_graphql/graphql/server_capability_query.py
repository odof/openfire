# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).


import graphene

from .server_capability_type import ServerCapability


class ServerCapabilityQuery(graphene.ObjectType):
    _name = "ServerCapabilityQuery"
    _type = "query"

    server_capabilities = graphene.List(
        graphene.NonNull(ServerCapability),
    )

    @staticmethod
    def resolve_server_capabilities(root, info):
        env = info.context["env"]

        capabilities = env["of.graphql"].server_capabilities()
        return [ServerCapability(name=k, enabled=v) for k, v in capabilities.items()]
