# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import graphene

from odoo.addons.graphql_base import OdooObjectType

from .account_tax_type import AccountTax, AccountTaxInput


class Product(OdooObjectType):
    _name = 'Product'
    _type = 'types'

    taxes_id = graphene.List(graphene.NonNull(AccountTax), required=True, name='taxes')


class ProductInput(graphene.InputObjectType):
    _name = 'ProductInput'
    _type = 'types'

    taxes = graphene.List(graphene.NonNull(AccountTaxInput))
