# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import graphene

from odoo.addons.of_base_graphql.graphql.partner_type import PartnerInput
from odoo.addons.of_graphql.graphql.odoo_graphql import lazy_delete

from .picking_type import Picking
from .stock_location_type import StockLocationInput
from .stock_move_type import StockMoveInput


class PickingCreate(graphene.Mutation):
    _name = 'PickingCreate'

    class Arguments:
        name = graphene.String()
        partner = graphene.Argument(PartnerInput)
        lines = graphene.List(graphene.NonNull(StockMoveInput))
        location = graphene.Argument(StockLocationInput)

    Output = Picking

    def mutate(self, info, **args):
        env = info.context['env']
        values = env['stock.picking']._prepare_mutation_values(**args)
        return env['stock.picking'].create(values)


class PickingUpdate(graphene.Mutation):
    _name = 'PickingUpdate'

    class Arguments:
        id = graphene.Int(required=True)
        name = graphene.String()
        partner = graphene.Argument(PartnerInput)
        lines = graphene.List(graphene.NonNull(StockMoveInput))
        location = graphene.Argument(StockLocationInput)

    Output = Picking

    def mutate(self, info, id, **args):
        env = info.context['env']
        values = env['stock.picking']._prepare_mutation_values(**args)
        picking = env['stock.picking'].search([('id', '=', id)])
        picking.write(values)
        return picking


class PickingDelete(graphene.Mutation):
    _name = 'PickingDelete'

    class Arguments:
        id = graphene.Int(required=True)

    Output = Picking

    def mutate(self, info, id):
        env = info.context['env']

        return lazy_delete(env, 'stock.picking', id)


class PickingMutation(graphene.ObjectType):
    _name = 'PickingMutation'
    _type = 'mutation'

    picking_create = PickingCreate.Field()
    picking_update = PickingUpdate.Field()
    picking_delete = PickingDelete.Field()
