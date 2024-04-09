import graphene

from odoo.addons.of_account_graphql.graphql.account_tax_mutation import AccountTaxCreate, AccountTaxUpdate
from odoo.addons.of_account_graphql.graphql.account_tax_type import AccountTaxInput
from odoo.addons.of_base_graphql.graphql.product_mutation import ProductCreate, ProductUpdate
from odoo.addons.of_base_graphql.graphql.product_type import ProductInput
from odoo.addons.of_graphql.graphql.odoo_graphql import lazy_create, lazy_delete, lazy_update

from .sale_order_line_type import SaleOrderLine, SaleOrderLineCreateInput, SaleOrderLineUpdateInput


class SaleOrderLineCreate(graphene.Mutation):
    _name = 'SaleOrderLineCreate'

    class Arguments:
        input = SaleOrderLineCreateInput(required=True)
        product = ProductInput()
        taxes = graphene.List(graphene.NonNull(AccountTaxInput))

    Output = SaleOrderLine

    def mutate(self, info, input, product=None, taxes=None):
        env = info.context["env"]

        create_taxes = env['account.tax']

        if taxes:
            for taxe in taxes:
                if taxe.id:
                    # on est sur une mise à jour
                    taxe = AccountTaxUpdate().mutate(info, id=taxe.id, input=taxe)
                else:
                    taxe = AccountTaxCreate().mutate(info, input=taxe)
                create_taxes += taxe

        if product:
            if product.id:
                product = ProductUpdate().mutate(info, id=product.id, input=product)
            else:
                product = ProductCreate().mutate(info, input=product)

        sale_order_line = lazy_create(env, "sale.order.line", input)

        if product:
            sale_order_line.product_id = product

        if taxes:
            sale_order_line.tax_id = [(6, 0, taxes.ids)]

        return sale_order_line


class SaleOrderLineUpdate(graphene.Mutation):
    _name = 'SaleOrderLineUpdate'

    class Arguments:
        id = graphene.Int(required=True)
        input = SaleOrderLineUpdateInput(required=True)
        product = ProductInput()
        taxes = graphene.List(graphene.NonNull(AccountTaxInput))

    Output = SaleOrderLine

    def mutate(self, info, id, input, product=None, taxes=None):
        env = info.context["env"]

        update_taxes = env['account.tax']

        if taxes:
            for taxe in taxes:
                if taxe.id:
                    # on est sur une mise à jour
                    taxe = AccountTaxUpdate().mutate(info, id=taxe.id, input=taxe)
                else:
                    taxe = AccountTaxCreate().mutate(info, input=taxe)
                update_taxes += taxe

        if product:
            if product.id:
                product = ProductUpdate().mutate(info, id=product.id, input=product)
            else:
                product = ProductCreate().mutate(info, input=product)

        sale_order_line = lazy_update(env, "sale.order.line", id, input)

        if product:
            sale_order_line.product_id = product

        if taxes:
            sale_order_line.tax_id = [(6, 0, taxes.ids)]

        return sale_order_line


class SaleOrderLineDelete(graphene.Mutation):
    _name = 'SaleOrderLineDelete'

    class Arguments:
        id = graphene.Int(required=True)

    Output = SaleOrderLine

    def mutate(self, info, id):
        env = info.context["env"]

        return lazy_delete(env, "sale.order.line", id)


class SaleOrderLineMutation(graphene.ObjectType):
    _name = 'SaleOrderLineMutation'
    _type = 'mutation'

    sale_order_line_create = SaleOrderLineCreate.Field()
    sale_order_line_update = SaleOrderLineUpdate.Field()
    sale_order_line_delete = SaleOrderLineDelete.Field()
