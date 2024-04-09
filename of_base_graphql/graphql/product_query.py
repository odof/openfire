import graphene

from odoo.addons.of_graphql.graphql.odoo_domain import OdooDomainInput
from odoo.addons.of_graphql.graphql.odoo_type import graphqlOdooDomain

from .product_type import Product, ProductFilterInput


class ProductQuery(graphene.ObjectType):
    _name = 'ProductQuery'
    _type = 'query'

    products = graphene.List(
        graphene.NonNull(Product),
        filter=graphene.Argument(ProductFilterInput),
        domain=graphene.List(graphene.NonNull(OdooDomainInput)),
        limit=graphene.Int(),
        offset=graphene.Int(),
    )

    @staticmethod
    def resolve_products(root, info, filter=None, domain=None, offset=0, limit=10):
        env = info.context['env']
        odoo_domain = []
        odoo_type = {'id': 'int', 'categ_id': 'int', 'list_price': 'float', 'company_id': 'int', 'of_mobile': 'boolean'}
        if domain:
            odoo_domain = graphqlOdooDomain(odoo_type, domain)

        if filter:
            if filter.name:
                odoo_domain += [('name', 'ilike', filter.name)]
            if filter.ref:
                odoo_domain += [('ref', 'ilike', filter.ref)]

        return env['product.product'].search(odoo_domain, offset=offset, limit=limit)
