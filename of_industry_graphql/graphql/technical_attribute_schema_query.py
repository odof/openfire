# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import graphene

from .technical_attribute_schema_type import TechnicalAttributeSchema


class TechnicalAttributeSchemaQuery(graphene.ObjectType):
    _name = "TechnicalAttributeSchemaQuery"
    _type = "query"

    technical_attribute_schemas = graphene.List(
        graphene.NonNull(TechnicalAttributeSchema),
    )

    @staticmethod
    def resolve_technical_attribute_schemas(root, info):
        env = info.context["env"]
        return env["product.template"]._prepare_technical_attribute_schemas()
