# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

import graphene

from odoo.addons.graphql_base import OdooObjectType
from odoo.addons.of_base_graphql.graphql.partner_type import Partner
from odoo.addons.of_base_graphql.graphql.product_category_type import ProductCategory
from odoo.addons.of_base_graphql.graphql.product_type import Product
from odoo.addons.of_product_brand_graphql.graphql.product_brand_type import ProductBrand
from odoo.addons.of_stock_graphql.graphql.stock_lot_type import StockLot


class Equipment(OdooObjectType):
    _name = "Equipment"
    _type = "types"

    id = graphene.Int(required=True)
    name = graphene.String()
    warranty_type = graphene.String()
    state = graphene.String()
    model_name = graphene.String()
    installation_type = graphene.String()
    is_compliant = graphene.Boolean()
    piece_number = graphene.String()
    note = graphene.String()
    service_date = graphene.Date()
    installation_date = graphene.Date()
    end_warranty_date = graphene.Date()

    product = graphene.Field(Product, required=True)
    brand = graphene.Field(ProductBrand)
    product_category = graphene.Field(ProductCategory)
    lot = graphene.Field(StockLot)
    reseller = graphene.Field(Partner)
    installer = graphene.Field(Partner)
    site_address_id = graphene.Field(Partner, name="siteAddress")

    @staticmethod
    def resolve_product(root, info):
        return root.product_id or None

    @staticmethod
    def resolve_brand(root, info):
        return root.brand_id or None

    @staticmethod
    def resolve_product_category(root, info):
        return root.product_category_id or None

    @staticmethod
    def resolve_lot(root, info):
        return root.lot_id or None

    @staticmethod
    def resolve_reseller(root, info):
        return root.reseller_id or None

    @staticmethod
    def resolve_installer(root, info):
        return root.installer_id or None


class EquipmentInput(graphene.InputObjectType):
    _name = "EquipmentInput"
    _type = "types"

    id = graphene.Int()
    name = graphene.String()
    warranty_type = graphene.String()
    state = graphene.String()
    model_name = graphene.String()
    installation_type = graphene.String()
    is_compliant = graphene.Boolean()
    piece_number = graphene.String()
    note = graphene.String()
    service_date = graphene.Date()
    installation_date = graphene.Date()
    end_warranty_date = graphene.Date()


class EquipmentFilterInput(EquipmentInput):
    _name = "EquipmentFilterInput"


class EquipmentCreateInput(EquipmentInput):
    _name = "EquipmentCreateInput"


class EquipmentUpdateInput(EquipmentInput):
    _name = "EquipmentUpdateInput"
