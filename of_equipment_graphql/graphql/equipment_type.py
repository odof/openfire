# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import graphene

from odoo.addons.graphql_base import OdooObjectType
from odoo.addons.of_base_graphql.graphql.partner_type import Partner, PartnerInput
from odoo.addons.of_base_graphql.graphql.product_category_type import ProductCategory, ProductCategoryInput
from odoo.addons.of_base_graphql.graphql.product_type import Product, ProductInput
from odoo.addons.of_planning_graphql.graphql.planning_intervention_type import (
    PlanningIntervention,
    PlanningInterventionInput,
)
from odoo.addons.of_product_brand_graphql.graphql.product_brand_type import ProductBrand, ProductBrandInput
from odoo.addons.of_stock_graphql.graphql.stock_lot_type import StockLot, StockLotInput


class Equipment(OdooObjectType):
    _name = 'Equipment'
    _type = 'types'

    id = graphene.Int(required=True)
    name = graphene.String()
    warranty_type = graphene.String()
    state = graphene.NonNull(graphene.String)
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
    site_address = graphene.Field(Partner)
    customer = graphene.Field(Partner, required=True)
    interventions = graphene.List(graphene.NonNull(PlanningIntervention))

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

    @staticmethod
    def resolve_site_address(root, info):
        return root.site_address_id or None

    @staticmethod
    def resolve_customer(root, info):
        return root.customer_id or None

    @staticmethod
    def resolve_interventions(root, info):
        env = info.context['env']
        return env['calendar.event'].search([('of_equipment_ids', 'in', root.id)])


class EquipmentInput(graphene.InputObjectType):
    _name = 'EquipmentInput'
    _type = 'types'

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
    product = graphene.Field(ProductInput)
    brand = graphene.Field(ProductBrandInput)
    product_category = graphene.Field(ProductCategoryInput)
    lot = graphene.Field(StockLotInput)
    reseller = graphene.Field(PartnerInput)
    installer = graphene.Field(PartnerInput)
    site_address = graphene.Field(PartnerInput)
    customer = graphene.Field(PartnerInput)
    interventions = graphene.List(graphene.NonNull(PlanningInterventionInput))


class EquipmentFilterInput(EquipmentInput):
    _name = 'EquipmentFilterInput'
