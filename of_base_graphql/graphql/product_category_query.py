# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

import graphene

from odoo.addons.of_graphql.graphql.odoo_domain import OdooDomainInput

from .product_category_type import ProductCategory, ProductCategoryFilterInput


class ProductCategoryQuery(graphene.ObjectType):
    _name = 'ProductCategoryQuery'
    _type = 'query'

    product_categories = graphene.List(
        graphene.NonNull(ProductCategory),
        select=graphene.Argument(ProductCategoryFilterInput),
        domain=graphene.List(graphene.NonNull(OdooDomainInput)),
        limit=graphene.Int(),
        offset=graphene.Int(),
    )

    @staticmethod
    def resolve_product_categories(root, info, select=None, domain=None, offset=0, limit=10):
        env = info.context['env']

        odoo_domain = env['product.category']._prepare_graphql_domain(select=select, domain=domain)

        return env['product.category'].search(odoo_domain, offset=offset, limit=limit)
