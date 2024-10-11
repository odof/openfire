# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import graphene

from odoo.addons.graphql_base import OdooObjectType
from odoo.addons.of_base_graphql.graphql.partner_type import Partner
from odoo.addons.of_base_graphql.graphql.product_template_type import ProductTemplate, ProductTemplateInput
from odoo.addons.of_base_graphql.graphql.product_type import Product, ProductInput


class ProductBrand(OdooObjectType):
    _name = "ProductBrand"
    _type = "types"

    id = graphene.Int(required=True)
    active = graphene.Boolean()
    code = graphene.String(required=True)
    name = graphene.String(required=True)
    use_prefix = graphene.Boolean()
    partner_id = graphene.Field(Partner, name="partner")
    supplier_delay = graphene.Int()
    product_ids = graphene.List(graphene.NonNull(ProductTemplate), name="productTemplates")
    product_variant_ids = graphene.List(graphene.NonNull(Product, name="products"))


class ProductBrandInput(graphene.InputObjectType):
    _name = "ProductBrandInput"
    _type = "types"

    id = graphene.Int()
    name = graphene.String()
    active = graphene.Boolean(default=True)
    code = graphene.String()
    use_prefix = graphene.Boolean()
    supplier_delay = graphene.Int()
    product_templates = graphene.List(graphene.NonNull(ProductTemplateInput))
    products = graphene.List(graphene.NonNull(ProductInput))


class ProductBrandFilterInput(ProductBrandInput):
    _name = "ProductBrandFilterInput"
