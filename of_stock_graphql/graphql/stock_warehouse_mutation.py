import graphene

from odoo.addons.of_base_graphql.graphql.partner_mutation import PartnerCreate, PartnerUpdate
from odoo.addons.of_base_graphql.graphql.partner_type import PartnerInput
from odoo.addons.of_graphql.graphql.odoo_graphql import lazy_create, lazy_delete, lazy_update

from .stock_warehouse_type import StockWarehouse, StockWarehouseCreateInput, StockWarehouseUpdateInput


class StockWarehouseCreate(graphene.Mutation):
    _name = 'StockWarehouseCreate'

    class Arguments:
        input = StockWarehouseCreateInput(required=True)
        partner = PartnerInput()

    Output = StockWarehouse

    def mutate(self, info, input, partner=None):
        env = info.context["env"]

        if partner:
            if partner.id:
                partner = PartnerUpdate().mutate(info, id=partner.id, input=partner)
            else:
                partner = PartnerCreate().mutate(info, input=partner)

        stock_warehouse = lazy_create(env, 'stock.warehouse', input)

        if partner:
            stock_warehouse.partner_id = partner

        return stock_warehouse


class StockWarehouseUpdate(graphene.Mutation):
    _name = 'StockWarehouseUpdate'

    class Arguments:
        id = graphene.Int(required=True)
        input = StockWarehouseUpdateInput(required=True)
        partner = PartnerInput()

    Output = StockWarehouse

    def mutate(self, info, id, input, partner=None):
        env = info.context["env"]

        if partner:
            if partner.id:
                partner = PartnerUpdate().mutate(info, id=partner.id, input=partner)
            else:
                partner = PartnerCreate().mutate(info, input=partner)

        stock_warehouse = lazy_update(env, 'stock.warehouse', id, input)

        if partner:
            stock_warehouse.partner_id = partner

        return stock_warehouse


class StockWarehouseDelete(graphene.Mutation):
    _name = 'StockWarehouseDelete'

    class Arguments:
        id = graphene.Int(required=True)

    Output = StockWarehouse

    def mutate(self, info, id):
        env = info.context['env']
        return lazy_delete(env, 'stock.warehouse', id)


class StockWarehouseMutation(graphene.ObjectType):
    _name = 'StockWarehouseMutation'
    _type = 'mutation'

    stock_warehouse_create = StockWarehouseCreate.Field()
    stock_warehouse_update = StockWarehouseUpdate.Field()
    stock_warehouse_delete = StockWarehouseDelete.Field()
