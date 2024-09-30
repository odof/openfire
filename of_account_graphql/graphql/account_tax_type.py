# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import graphene

from odoo.addons.graphql_base import OdooObjectType


class AccountTaxType(graphene.Enum):
    SALE = "sale"
    PURCHASE = "purchase"
    NONE = "none"


class AccountTax(OdooObjectType):
    _name = "AccountTax"
    _type = "types"

    id = graphene.Int(required=True)
    name = graphene.String(required=True)
    amount = graphene.Float(required=True)
    price_include = graphene.Boolean(required=True)
    type_tax_use = graphene.Field(AccountTaxType, required=True)


class AccountTaxInput(graphene.InputObjectType):
    _name = "AccountInput"
    _type = "types"

    id = graphene.Int()
    name = graphene.String()
    amount = graphene.Float()
    price_include = graphene.Boolean()


class AccountTaxFilterInput(AccountTaxInput):
    _name = "AccountFilterInput"
