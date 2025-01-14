# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import graphene

from odoo.addons.graphql_base import OdooObjectType
from odoo.addons.of_industry_graphql.graphql.technical_attribute_type import TechnicalAttribute, TechnicalAttributeInput


class Equipment(OdooObjectType):
    _name = "Equipment"
    _type = "types"

    technical_attributes = graphene.List(TechnicalAttribute)

    def resolve_technical_attributes(root, info):
        attributes = root._prepare_technical_attributes()
        return attributes


class EquipmentInput(graphene.InputObjectType):
    _name = "EquipmentInput"
    _type = "types"

    technical_attributes = graphene.List(TechnicalAttributeInput)
