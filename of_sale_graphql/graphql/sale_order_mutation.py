# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import graphene

from odoo.addons.of_account_graphql.graphql.account_payment_term_type import AccountPaymentTermInput
from odoo.addons.of_base_graphql.graphql.partner_type import PartnerInput
from odoo.addons.of_graphql.graphql.odoo_graphql import lazy_delete
from odoo.addons.of_graphql.graphql.user_type import UserInput

from .sale_order_line_type import SaleOrderLineInput
from .sale_order_type import SaleOrder


class SaleOrderCreate(graphene.Mutation):
    _name = "SaleOrderCreate"

    class Arguments:
        name = graphene.String()
        date_order = graphene.DateTime()
        validity_date = graphene.Date()
        partner = graphene.Argument(PartnerInput)
        lines = graphene.List(graphene.NonNull(SaleOrderLineInput))
        state = graphene.String()
        payment_term = graphene.Argument(AccountPaymentTermInput)
        vendor = graphene.Argument(UserInput)

    Output = SaleOrder

    def mutate(self, info, **args):
        env = info.context["env"]
        values = env["sale.order"]._prepare_mutation_values(**args)
        return env["sale.order"].create(values)


class SaleOrderUpdate(graphene.Mutation):
    _name = "SaleOrderUpdate"

    class Arguments:
        id = graphene.Int(required=True)
        name = graphene.String()
        date_order = graphene.DateTime()
        validity_date = graphene.Date()
        partner = graphene.Argument(PartnerInput)
        lines = graphene.List(graphene.NonNull(SaleOrderLineInput))
        state = graphene.String()
        payment_term = graphene.Argument(AccountPaymentTermInput)
        vendor = graphene.Argument(UserInput)

    Output = SaleOrder

    def mutate(self, info, id, **args):
        env = info.context["env"]
        values = env["sale.order"]._prepare_mutation_values(**args)
        order = env["sale.order"].search([("id", "=", id)])
        order.write(values)
        return order


class SaleOrderDelete(graphene.Mutation):
    _name = "SaleOrderDelete"

    class Arguments:
        id = graphene.Int(required=True)

    Output = SaleOrder

    def mutate(self, info, id):
        env = info.context["env"]

        return lazy_delete(env, "sale.order", id)


class SaleOrderMutation(graphene.ObjectType):
    _name = "SaleOrderMutation"
    _type = "mutation"

    sale_order_create = SaleOrderCreate.Field()
    sale_order_update = SaleOrderUpdate.Field()
    sale_order_delete = SaleOrderDelete.Field()
