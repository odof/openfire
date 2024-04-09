# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

import graphene

from odoo.addons.of_graphql.graphql.odoo_domain import OdooDomainInput
from odoo.addons.of_graphql.graphql.odoo_type import graphqlOdooDomain

from .product_category_type import ProductCategory, ProductCategoryFilterInput


class ProductCategoryQuery(graphene.ObjectType):
    _name = 'ProductCategoryQuery'
    _type = 'query'

    product_categories = graphene.List(
        graphene.NonNull(ProductCategory),
        filter=graphene.Argument(ProductCategoryFilterInput),
        domain=graphene.List(graphene.NonNull(OdooDomainInput)),
        limit=graphene.Int(),
        offset=graphene.Int(),
    )

    @staticmethod
    def resolve_product_categories(root, info, filter=None, domain=None, offset=0, limit=10):
        env = info.context['env']
        odoo_domain = []
        odoo_type = {
            'id': 'int',
        }
        if domain:
            odoo_domain = graphqlOdooDomain(odoo_type, domain)

        if filter:
            if filter.name:
                odoo_domain += [('name', 'ilike', filter.name)]
            if filter.id:
                odoo_domain += [('id', '=', filter.id)]

        return env['product.category'].search(odoo_domain, offset=offset, limit=limit)
