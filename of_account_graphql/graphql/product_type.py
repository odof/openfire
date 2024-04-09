import graphene

from odoo.addons.graphql_base import OdooObjectType

from .account_tax_type import AccountTax


class Product(OdooObjectType):
    _name = 'Product'
    _type = 'types'

    taxes_id = graphene.List(graphene.NonNull(AccountTax), required=True, name='taxes')
