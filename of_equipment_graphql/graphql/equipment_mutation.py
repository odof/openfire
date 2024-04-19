import logging

import graphene

from odoo.addons.of_base_graphql.graphql.partner_mutation import PartnerCreate, PartnerUpdate
from odoo.addons.of_base_graphql.graphql.partner_type import PartnerInput
from odoo.addons.of_base_graphql.graphql.product_category_mutation import ProductCategoryCreate, ProductCategoryUpdate
from odoo.addons.of_base_graphql.graphql.product_category_type import ProductCategoryInput
from odoo.addons.of_base_graphql.graphql.product_mutation import ProductCreate, ProductUpdate
from odoo.addons.of_base_graphql.graphql.product_type import ProductInput
from odoo.addons.of_graphql.graphql.odoo_graphql import lazy_create, lazy_delete, lazy_update
from odoo.addons.of_planning_graphql.graphql.planning_intervention_mutation import (
    PlanningInterventionCreate,
    PlanningInterventionUpdate,
)
from odoo.addons.of_planning_graphql.graphql.planning_intervention_type import PlanningInterventionInput
from odoo.addons.of_product_brand_graphql.graphql.product_brand_mutation import ProductBrandCreate, ProductBrandUpdate
from odoo.addons.of_product_brand_graphql.graphql.product_brand_type import ProductBrandInput
from odoo.addons.of_stock_graphql.graphql.stock_lot_mutation import StockLotCreate, StockLotUpdate
from odoo.addons.of_stock_graphql.graphql.stock_lot_type import StockLotInput

from .equipment_type import Equipment, EquipmentCreateInput, EquipmentUpdateInput

logger = logging.getLogger(__name__)


class EquipmentCreate(graphene.Mutation):
    _name = 'EquipmentCreate'

    class Arguments:
        input = EquipmentCreateInput(required=True)
        product = ProductInput(required=True)
        brand = ProductBrandInput()
        product_category = ProductCategoryInput()
        lot = StockLotInput()
        reseller = PartnerInput()
        installer = PartnerInput()
        customer = PartnerInput(required=True)
        intervention = PlanningInterventionInput()
        site_address = PartnerInput()

    Output = Equipment

    def mutate(
        self,
        info,
        input,
        product,
        customer,
        brand=None,
        product_category=None,
        lot=None,
        reseller=None,
        installer=None,
        intervention=None,
        site_address=None,
    ):
        env = info.context["env"]
        my_input = input.copy()

        if product.id:
            product = ProductUpdate().mutate(info, id=product.id, input=product)
        else:
            product = ProductCreate().mutate(info, input=product)

        my_input['product_id'] = product.id

        if customer.id:
            customer = PartnerUpdate().mutate(info, id=customer.id, input=customer)
        else:
            customer = PartnerCreate().mutate(info, input=customer)

        my_input['customer_id'] = customer.id

        if product_category:
            if product_category.id:
                product_category = ProductCategoryUpdate().mutate(info, id=product_category.id, input=product_category)
            else:
                product_category = ProductCategoryCreate().mutate(info, input=product_category)

        if brand:
            if brand.id:
                brand = ProductBrandUpdate().mutate(info, id=brand.id, input=brand)
            else:
                brand = ProductBrandCreate().mutate(info, input=brand)

        if lot:
            if lot.id:
                lot = StockLotUpdate().mutate(info, id=lot.id, input=lot)
            else:
                lot = StockLotCreate().mutate(info, input=lot)

        if reseller:
            if reseller.id:
                reseller = PartnerUpdate().mutate(info, id=reseller.id, input=reseller)
            else:
                reseller = PartnerCreate().mutate(info, input=reseller)

        if installer:
            if installer.id:
                installer = PartnerUpdate().mutate(info, id=installer.id, input=installer)
            else:
                installer = PartnerCreate().mutate(info, input=installer)

        if intervention:
            if intervention.id:
                intervention = PlanningInterventionUpdate().mutate(info, id=intervention.id, input=intervention)
            else:
                intervention = PlanningInterventionCreate().mutate(info, input=intervention)
            intervention.of_use_equipment = True

        if site_address:
            if site_address.id:
                site_address = PartnerUpdate().mutate(info, id=site_address.id, input=site_address)
            else:
                site_address = PartnerCreate().mutate(info, input=site_address)

        equipment = lazy_create(env, 'of.equipment', my_input)

        if brand:
            equipment.brand_id = brand.id

        if product_category:
            equipment.product_category_id = product_category.id

        if lot:
            equipment.lot_id = lot.id

        if reseller:
            equipment.reseller_id = reseller.id

        if installer:
            equipment.installer_id = installer.id

        if intervention:
            equipment.intervention_ids += intervention

        if site_address:
            equipment.site_address_id = site_address.id

        return equipment


class EquipmentUpdate(graphene.Mutation):
    _name = 'EquipmentUpdate'

    class Arguments:
        id = graphene.Int(required=True)
        input = EquipmentUpdateInput(required=True)
        product = ProductInput()
        brand = ProductBrandInput()
        product_category = ProductCategoryInput()
        lot = StockLotInput()
        reseller = PartnerInput()
        installer = PartnerInput()
        customer = PartnerInput()
        intervention = PlanningInterventionInput()
        site_address = PartnerInput()

    Output = Equipment

    def mutate(
        self,
        info,
        id,
        input,
        product=None,
        customer=None,
        brand=None,
        product_category=None,
        lot=None,
        reseller=None,
        installer=None,
        intervention=None,
        site_address=None,
    ):
        env = info.context["env"]

        if product:
            if product.id:
                product = ProductUpdate().mutate(info, id=product.id, input=product)
            else:
                product = ProductCreate().mutate(info, input=product)

        if customer:
            if customer.id:
                customer = PartnerUpdate().mutate(info, id=customer.id, input=customer)
            else:
                customer = PartnerCreate().mutate(info, input=customer)

        if product_category:
            if product_category.id:
                product_category = ProductCategoryUpdate().mutate(info, id=product_category.id, input=product_category)
            else:
                product_category = ProductCategoryCreate().mutate(info, input=product_category)

        if brand:
            if brand.id:
                brand = ProductBrandUpdate().mutate(info, id=brand.id, input=brand)
            else:
                brand = ProductBrandCreate().mutate(info, input=brand)

        if lot:
            if lot.id:
                lot = StockLotUpdate().mutate(info, id=lot.id, input=lot)
            else:
                lot = StockLotCreate().mutate(info, input=lot)

        if reseller:
            if reseller.id:
                reseller = PartnerUpdate().mutate(info, id=reseller.id, input=reseller)
            else:
                reseller = PartnerCreate().mutate(info, input=reseller)

        if installer:
            if installer.id:
                installer = PartnerUpdate().mutate(info, id=installer.id, input=installer)
            else:
                installer = PartnerCreate().mutate(info, input=installer)

        if intervention:
            if intervention.id:
                intervention = PlanningInterventionUpdate().mutate(info, id=intervention.id, input=intervention)
            else:
                intervention = PlanningInterventionCreate().mutate(info, input=intervention)
            intervention.of_use_equipment = True

        if site_address:
            if site_address.id:
                site_address = PartnerUpdate().mutate(info, id=site_address.id, input=site_address)
            else:
                site_address = PartnerCreate().mutate(info, input=site_address)

        equipment = lazy_update(env, 'of.equipment', id, input)

        if product:
            equipment.product_id = product.id

        if customer:
            equipment.customer_id = customer.id

        if brand:
            equipment.brand_id = brand.id

        if product_category:
            equipment.product_category_id = product_category.id

        if lot:
            equipment.lot_id = lot.id

        if reseller:
            equipment.reseller_id = reseller.id

        if installer:
            equipment.installer_id = installer.id

        if intervention:
            equipment.intervention_ids += intervention

        if site_address:
            equipment.site_address_id = site_address.id

        return equipment


class EquipmentDelete(graphene.Mutation):
    _name = 'EquipmentDelete'

    class Arguments:
        id = graphene.Int(required=True)

    Output = Equipment

    def mutate(self, info, id):
        env = info.context['env']

        equipment = env['calendar.event'].browse(id)
        # On va vérifier dans chaque intervention sur cet équipement, s'il n'y a pas d'autres équipements
        # alors on passe le champ use_equipment à False
        if equipment:
            for intervention in equipment.intervention_ids:
                if len(intervention.of_equipment_ids.filtered(lambda r: r.id != equipment.id)) == 0:
                    intervention.of_use_equipment = False

        return lazy_delete(env, 'of.equipment', id)


class EquipmentMutation(graphene.ObjectType):
    _name = 'EquipmentMutation'
    _type = 'mutation'

    equipment_create = EquipmentCreate.Field()
    equipment_update = EquipmentUpdate.Field()
    equipment_delete = EquipmentDelete.Field()
