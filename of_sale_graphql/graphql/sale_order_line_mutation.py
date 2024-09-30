# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import graphene

from odoo.addons.of_account_graphql.graphql.account_tax_type import AccountTaxInput
from odoo.addons.of_base_graphql.graphql.product_type import ProductInput
from odoo.addons.of_graphql.graphql.odoo_graphql import lazy_delete

from .sale_order_line_type import SaleOrderLine


class SaleOrderLineCreate(graphene.Mutation):
    _name = "SaleOrderLineCreate"

    class Arguments:
        name = graphene.String()
        product_uom_qty = graphene.Float()
        price_unit = graphene.Float()
        price_subtotal = graphene.Float()
        product = graphene.Argument(ProductInput)
        taxes = graphene.List(graphene.NonNull(AccountTaxInput))

    Output = SaleOrderLine

    def mutate(self, info, **args):
        env = info.context["env"]
        values = env["sale.order.line"]._prepare_mutation_values(**args)
        return env["sale.order.line"].create(values)


class SaleOrderLineUpdate(graphene.Mutation):
    _name = "SaleOrderLineUpdate"

    class Arguments:
        id = graphene.Int(required=True)
        name = graphene.String()
        product_uom_qty = graphene.Float()
        price_unit = graphene.Float()
        price_subtotal = graphene.Float()
        product = graphene.Argument(ProductInput)
        taxes = graphene.List(graphene.NonNull(AccountTaxInput))

    Output = SaleOrderLine

    def mutate(self, info, id, **args):
        env = info.context["env"]
        values = env["sale.order.line"]._prepare_mutation_values(**args)
        line = env["sale.order.line"].search([("id", "=", id)])
        line.write(values)
        return line


class SaleOrderLineDelete(graphene.Mutation):
    _name = "SaleOrderLineDelete"

    class Arguments:
        id = graphene.Int(required=True)

    Output = SaleOrderLine

    def mutate(self, info, id):
        env = info.context["env"]

        return lazy_delete(env, "sale.order.line", id)


class SaleOrderLineMutation(graphene.ObjectType):
    _name = "SaleOrderLineMutation"
    _type = "mutation"

    sale_order_line_create = SaleOrderLineCreate.Field()
    sale_order_line_update = SaleOrderLineUpdate.Field()
    sale_order_line_delete = SaleOrderLineDelete.Field()
