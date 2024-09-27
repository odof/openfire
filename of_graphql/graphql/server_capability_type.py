# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import graphene


class ServerCapability(graphene.ObjectType):
    _name = "ServerCapability"
    _type = "types"

    def __init__(self, name, enabled):
        self.name = name
        self.enabled = enabled

    name = graphene.String(required=True)
    enabled = graphene.Boolean()
