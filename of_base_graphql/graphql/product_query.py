import graphene

from odoo.addons.of_graphql.graphql.odoo_domain import OdooDomainInput

from .product_type import Product, ProductFilterInput


class ProductQuery(graphene.ObjectType):
    _name = 'ProductQuery'
    _type = 'query'

    products = graphene.List(
        graphene.NonNull(Product),
        select=graphene.Argument(ProductFilterInput),
        domain=graphene.List(graphene.NonNull(OdooDomainInput)),
        limit=graphene.Int(),
        offset=graphene.Int(),
    )

    @staticmethod
    def resolve_products(root, info, select=None, domain=None, offset=0, limit=10):
        env = info.context['env']

        odoo_domain = env['product.product']._prepare_graphql_domain(select=select, domain=domain)
        return env['product.product'].search(odoo_domain, offset=offset, limit=limit)
