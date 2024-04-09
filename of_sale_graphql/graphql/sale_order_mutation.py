import graphene

from odoo.addons.of_base_graphql.graphql.partner_mutation import PartnerCreate, PartnerUpdate
from odoo.addons.of_base_graphql.graphql.partner_type import PartnerInput
from odoo.addons.of_graphql.graphql.odoo_graphql import lazy_create, lazy_delete, lazy_update

from .sale_order_line_mutation import SaleOrderLineCreate, SaleOrderLineUpdate
from .sale_order_line_type import SaleOrderLineInput
from .sale_order_type import SaleOrder, SaleOrderCreateInput, SaleOrderUpdateInput


class SaleOrderCreate(graphene.Mutation):
    _name = 'SaleOrderCreate'

    class Arguments:
        input = SaleOrderCreateInput(required=True)
        partner = PartnerInput()
        lines = graphene.List(graphene.NonNull(SaleOrderLineInput))

    Output = SaleOrder

    def mutate(self, info, input, partner=None, lines=None):
        env = info.context["env"]
        create_lines = env['sale.order.line']

        if partner:
            if partner.id:
                partner = PartnerUpdate().mutate(info, id=partner.id, input=partner)
            else:
                partner = PartnerCreate().mutate(info, input=partner)

        if lines:
            for line in lines:
                if line.id:
                    line = SaleOrderLineUpdate().mutate(info, id=line.id, input=line)
                else:
                    line = SaleOrderLineCreate().mutate(info, input=line)
                create_lines += line

        sale_order = lazy_create(env, "sale.order", input)

        if partner:
            sale_order.partner_id = partner

        if lines:
            sale_order.order_line = [(6, 0, create_lines.ids)]

        return sale_order


class SaleOrderUpdate(graphene.Mutation):
    _name = 'SaleOrderUpdate'

    class Arguments:
        id = graphene.Int(required=True)
        input = SaleOrderUpdateInput(required=True)
        partner = PartnerInput()
        lines = graphene.List(graphene.NonNull(SaleOrderLineInput))

    Output = SaleOrder

    def mutate(self, info, id, input, partner=None, lines=None):
        env = info.context["env"]
        update_lines = env['sale.order.line']

        if partner:
            if partner.id:
                partner = PartnerUpdate().mutate(info, id=partner.id, input=partner)
            else:
                partner = PartnerCreate().mutate(info, input=partner)

        if lines:
            for line in lines:
                if line.id:
                    line = SaleOrderLineUpdate().mutate(info, id=line.id, input=line)
                else:
                    line = SaleOrderLineCreate().mutate(info, input=line)
                update_lines += line

        sale_order = lazy_update(env, "sale.order", id, input)

        if partner:
            sale_order.partner_id = partner

        if lines:
            sale_order.order_line = [(6, 0, update_lines.ids)]

        return sale_order


class SaleOrderDelete(graphene.Mutation):
    _name = 'SaleOrderDelete'

    class Arguments:
        id = graphene.Int(required=True)

    Output = SaleOrder

    def mutate(self, info, id):
        env = info.context["env"]

        return lazy_delete(env, "sale.order", id)


class SaleOrderMutation(graphene.ObjectType):
    _name = 'SaleOrderMutation'
    _type = 'mutation'

    sale_order_create = SaleOrderCreate.Field()
    sale_order_update = SaleOrderUpdate.Field()
    sale_order_delete = SaleOrderDelete.Field()
