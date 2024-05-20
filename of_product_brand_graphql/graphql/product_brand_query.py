# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

import graphene

from odoo.addons.of_graphql.graphql.odoo_domain import OdooDomainInput

from .product_brand_type import ProductBrand, ProductBrandFilterInput


class ProductBrandQuery(graphene.ObjectType):
    _name = 'ProductBrandQuery'
    _type = 'query'

    product_brands = graphene.List(
        graphene.NonNull(ProductBrand),
        select=graphene.Argument(ProductBrandFilterInput),
        domain=graphene.List(graphene.NonNull(OdooDomainInput)),
        limit=graphene.Int(),
        offset=graphene.Int(),
    )

    @staticmethod
    def resolve_product_brands(root, info, select=None, domain=None, offset=0, limit=10):
        env = info.context['env']

        odoo_domain = env['of.product.brand']._prepare_graphql_domain(select=select, domain=domain)

        return env['of.product.brand'].search(odoo_domain, offset=offset, limit=limit)
