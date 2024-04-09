import graphene

from odoo.addons.of_base_graphql.graphql.partner_mutation import PartnerCreate, PartnerUpdate
from odoo.addons.of_base_graphql.graphql.partner_type import PartnerInput
from odoo.addons.of_graphql.graphql.odoo_graphql import lazy_create, lazy_delete, lazy_update
from odoo.addons.of_stock_graphql.graphql.stock_location_mutation import StockLocationCreate, StockLocationUpdate

from .picking_type import Picking, PickingCreateInput, PickingUpdateInput
from .stock_location_type import StockLocationInput
from .stock_move_mutation import StockMoveCreate, StockMoveUpdate
from .stock_move_type import StockMoveInput


class PickingCreate(graphene.Mutation):
    _name = 'PickingCreate'

    class Arguments:
        input = PickingCreateInput(required=True)
        partner = PartnerInput()
        lines = graphene.List(graphene.NonNull(StockMoveInput))
        location = StockLocationInput()

    Output = Picking

    def mutate(self, info, input, partner=None, lines=None, location=None):
        env = info.context["env"]
        create_lines = env['stock.move']

        if partner:
            if partner.id:
                partner = PartnerUpdate().mutate(info, id=partner.id, input=partner)
            else:
                partner = PartnerCreate().mutate(info, input=partner)

        if lines:
            for line in lines:
                if line.id:
                    line = StockMoveUpdate().mutate(info, id=line.id, input=line)
                else:
                    line = StockMoveCreate().mutate(info, input=line)
                create_lines += line

        if location:
            if location.id:
                location = StockLocationUpdate().mutate(info, id=location.id, input=location)
            else:
                location = StockLocationCreate().mutate(info, input=location)

        picking = lazy_create(env, "stock.picking", input)

        if partner:
            picking.partner_id = partner

        if lines:
            picking.move_ids_without_package = [(6, 0, create_lines.ids)]

        if picking:
            picking.location_id = location

        return picking


class PickingUpdate(graphene.Mutation):
    _name = 'PickingUpdate'

    class Arguments:
        id = graphene.Int(required=True)
        input = PickingUpdateInput(required=True)
        partner = PartnerInput()
        lines = graphene.List(graphene.NonNull(StockMoveInput))
        location = StockLocationInput()

    Output = Picking

    def mutate(self, info, id, input, partner=None, lines=None, location=None):
        env = info.context["env"]
        update_lines = env['stock.move']

        if partner:
            if partner.id:
                partner = PartnerUpdate().mutate(info, id=partner.id, input=partner)
            else:
                partner = PartnerCreate().mutate(info, input=partner)

        if lines:
            for line in lines:
                if line.id:
                    line = StockMoveUpdate().mutate(info, id=line.id, input=line)
                else:
                    line = StockMoveCreate().mutate(info, input=line)
                update_lines += line

        if location:
            if location.id:
                location = StockLocationUpdate().mutate(info, id=location.id, input=location)
            else:
                location = StockLocationCreate().mutate(info, input=location)

        picking = lazy_update(env, "stock.picking", id, input)

        if partner:
            picking.partner_id = partner

        if lines:
            picking.move_ids_without_package = [(6, 0, update_lines.ids)]

        if location:
            picking.location_id = location

        return picking


class PickingDelete(graphene.Mutation):
    _name = 'PickingDelete'

    class Arguments:
        id = graphene.Int(required=True)

    Output = Picking

    def mutate(self, info, id):
        env = info.context["env"]

        return lazy_delete(env, "stock.picking", id)


class PickingMutation(graphene.ObjectType):
    _name = 'PickingMutation'
    _type = 'mutation'

    picking_create = PickingCreate.Field()
    picking_update = PickingUpdate.Field()
    picking_delete = PickingDelete.Field()
