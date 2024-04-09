# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

import graphene

from .configuration_type import Configuration


class ConfigurationQuery(graphene.ObjectType):
    _name = "ConfigurationQuery"
    _type = "query"

    configuration = graphene.Field(Configuration)

    @staticmethod
    def resolve_configuration(root, info):
        return Configuration()
