# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import graphene

from odoo.models import expression

from odoo.addons.of_base_graphql.graphql.product_type import Product


class ProductQuery(graphene.ObjectType):
    _name = "PartnerQuery"
    _type = "query"

    additional_products = graphene.List(graphene.NonNull(Product))

    products_search = graphene.List(
        graphene.NonNull(Product),
        brand_ids=graphene.List(graphene.NonNull(graphene.Int)),
        category_ids=graphene.List(graphene.NonNull(graphene.Int)),
        query=graphene.String(required=True),
    )

    @staticmethod
    def resolve_additional_products(root, info):
        env = info.context["env"]
        return env["product.product"].search([("of_mobile_available", "=", True)])

    @staticmethod
    def resolve_products_search(root, info, query, brand_ids=[], category_ids=[]):
        env = info.context["env"]
        domain = [
            "|",
            ("name", "ilike", query),
            ("default_code", "ilike", query),
        ]

        if brand_ids:
            domain = expression.AND([domain, [("brand_id", "in", brand_ids)]])

        if category_ids:
            domain = expression.AND([domain, [("categ_id", "in", category_ids)]])

        return env["product.product"].search(domain, limit=20)
