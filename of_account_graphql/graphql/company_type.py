import graphene

from odoo.addons.graphql_base import OdooObjectType


class TaxCalculationRoundMethod(graphene.Enum):
    ROUND_PER_LINE = 'pround_per_line'
    ROUND_GLOBALLY = 'round_globally'


class Company(OdooObjectType):
    _name = 'Company'
    _type = "types"

    tax_calculation_rounding_method = graphene.String(required=True)
