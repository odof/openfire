# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

import graphene

from odoo.addons.graphql_base import OdooObjectType
from odoo.addons.of_account_graphql.graphql.account_tax_type import AccountTax, AccountTaxInput
from odoo.addons.of_base_graphql.graphql.product_type import Product, ProductInput


class PlanningInterventionLine(OdooObjectType):
    _name = 'PlanningInterventionLine'
    _type = 'types'

    id = graphene.Int(required=True)
    price_unit = graphene.NonNull(graphene.Float)
    name = graphene.String()
    discount = graphene.NonNull(graphene.Float)
    product_id = graphene.NonNull(Product, name='product')
    qty = graphene.NonNull(graphene.Float, name='quantity')
    tax_ids = graphene.NonNull(graphene.List(graphene.NonNull(AccountTax)), name='taxes')


class PlanningInterventionLineInput(graphene.InputObjectType):
    _name = 'PlanningInterventionLineInput'
    _type = 'types'

    id = graphene.Int()
    price_unit = graphene.NonNull(graphene.Float)
    name = graphene.String()
    discount = graphene.NonNull(graphene.Float)
    product = graphene.NonNull(ProductInput)
    quantity = graphene.NonNull(graphene.Float)
    taxes = graphene.NonNull(graphene.List(graphene.NonNull(AccountTaxInput)))
