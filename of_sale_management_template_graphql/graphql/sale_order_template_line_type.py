# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import graphene

from odoo.addons.graphql_base import OdooObjectType
from odoo.addons.of_base_graphql.graphql.company_type import CompanyInput
from odoo.addons.of_base_graphql.graphql.product_type import Product, ProductInput
from odoo.addons.of_graphql.graphql.company_type import Company


class SaleOrderTemplateLine(OdooObjectType):
    _name = "SaleOrderTemplateLine"
    _type = "types"

    id = graphene.Int(required=True)
    name = graphene.String(required=True)
    product = graphene.Field(Product, required=True)
    product_uom_qty = graphene.Float(required=True)
    company = graphene.Field(Company)

    @staticmethod
    def resolve_product(root, info):
        return root.product_id or None

    @staticmethod
    def resolve_company(root, info):
        return root.company_id or None


class SaleOrderTemplateLineInput(graphene.InputObjectType):
    _name = "SaleOrderTemplateLineInput"
    _type = "types"

    id = graphene.Int()
    name = graphene.String()
    product_uom_qty = graphene.Float()
    product = graphene.Field(ProductInput)
    company = graphene.Field(CompanyInput)


class SaleOrderTemplateLineFilterInput(SaleOrderTemplateLineInput):
    _name = "SaleOrderTemplateLineFilterInput"
