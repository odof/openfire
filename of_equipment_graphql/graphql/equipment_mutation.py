import logging

import graphene

from odoo.addons.of_base_graphql.graphql.partner_type import PartnerInput
from odoo.addons.of_base_graphql.graphql.product_category_type import ProductCategoryInput
from odoo.addons.of_base_graphql.graphql.product_type import ProductInput
from odoo.addons.of_graphql.graphql.odoo_graphql import lazy_delete
from odoo.addons.of_planning_graphql.graphql.planning_intervention_type import PlanningInterventionInput
from odoo.addons.of_product_brand_graphql.graphql.product_brand_type import ProductBrandInput
from odoo.addons.of_stock_graphql.graphql.stock_lot_type import StockLotInput

from .equipment_type import Equipment

logger = logging.getLogger(__name__)


class EquipmentCreate(graphene.Mutation):
    _name = 'EquipmentCreate'

    class Arguments:
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
        product = graphene.Argument(ProductInput)
        brand = graphene.Argument(ProductBrandInput)
        product_category = graphene.Argument(ProductCategoryInput)
        lot = graphene.Argument(StockLotInput)
        reseller = graphene.Argument(PartnerInput)
        installer = graphene.Argument(PartnerInput)
        customer = graphene.Argument(PartnerInput)
        intervention = graphene.Argument(PlanningInterventionInput)
        site_address = graphene.Argument(PartnerInput)

    Output = Equipment

    def mutate(self, info, **args):
        env = info.context["env"]
        values = env['of.equipment']._prepare_mutation_values(**args)
        return env['of.equipment'].create(values)


class EquipmentUpdate(graphene.Mutation):
    _name = 'EquipmentUpdate'

    class Arguments:
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
        product = graphene.Argument(ProductInput)
        brand = graphene.Argument(ProductBrandInput)
        product_category = graphene.Argument(ProductCategoryInput)
        lot = graphene.Argument(StockLotInput)
        reseller = graphene.Argument(PartnerInput)
        installer = graphene.Argument(PartnerInput)
        customer = graphene.Argument(PartnerInput)
        intervention = graphene.Argument(PlanningInterventionInput)
        site_address = graphene.Argument(PartnerInput)

    Output = Equipment

    def mutate(self, info, id, **args):
        env = info.context["env"]
        values = env['of.equipment']._prepare_mutation_values(**args)
        equipment = env['of.equipment'].search([('id', '=', id)])
        equipment.write(values)
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
