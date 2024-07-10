# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import graphene

from odoo.addons.graphql_base import OdooObjectType
from odoo.addons.of_base_graphql.graphql.product_type import Product, ProductInput


class PlanningInterventionTemplateAdditionalLine(OdooObjectType):
    _name = 'PlanningInterventionTemplateAdditionalLine'
    _type = 'types'

    product = graphene.Field(Product)
    price_unit = graphene.Float()

    @staticmethod
    def resolve_product(root, info):
        return root.product_id or None


class PlanningInterventionTemplateAdditionalLineInput(graphene.InputObjectType):
    _name = 'PlanningInterventionTemplateAdditionalLineInput'
    _type = 'types'

    product = graphene.Field(ProductInput)
    price_unit = graphene.Float()


class PlanningInterventionTemplateAdditionalLineFilterInput(PlanningInterventionTemplateAdditionalLineInput):
    _name = 'PlanningInterventionTemplateAdditionalLineFilterInput'
