# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import graphene

from odoo.addons.of_account_graphql.graphql.account_move_line_type import AccountMoveLineInput
from odoo.addons.of_base_graphql.graphql.company_type import CompanyInput
from odoo.addons.of_base_graphql.graphql.product_type import ProductInput
from odoo.addons.of_graphql.graphql.odoo_graphql import lazy_delete
from odoo.addons.of_sale_graphql.graphql.sale_order_line_type import SaleOrderLineInput

from .service_request_line_type import ServiceRequestLine


class ServiceRequestLineCreate(graphene.Mutation):
    _name = "ServiceRequestLineCreate"

    class Arguments:
        name = graphene.String()
        qty = graphene.Float()
        price_unit = graphene.Float()
        price_subtotal = graphene.Float()
        price_tax = graphene.Float()
        price_total = graphene.Float()
        invoice_status = graphene.String()
        qty_invoiced = graphene.Float()
        qty_invoiceable = graphene.Float()
        product = graphene.Argument(ProductInput)
        order_line = graphene.Argument(SaleOrderLineInput)
        company = graphene.Argument(CompanyInput)
        invoice_lines = graphene.List(graphene.NonNull(AccountMoveLineInput))

    Output = ServiceRequestLine

    def mutate(self, info, **args):
        env = info.context["env"]
        values = env["of.service.request.line"]._prepare_mutation_values(**args)
        return env["of.service.request.line"].create(values)


class ServiceRequestLineUpdate(graphene.Mutation):
    _name = "ServiceRequestLineUpdate"

    class Arguments:
        id = graphene.Int(required=True)
        name = graphene.String()
        qty = graphene.Float()
        price_unit = graphene.Float()
        price_subtotal = graphene.Float()
        price_tax = graphene.Float()
        price_total = graphene.Float()
        invoice_status = graphene.String()
        qty_invoiced = graphene.Float()
        qty_invoiceable = graphene.Float()
        product = graphene.Argument(ProductInput)
        order_line = graphene.Argument(SaleOrderLineInput)
        company = graphene.Argument(CompanyInput)
        invoice_lines = graphene.List(graphene.NonNull(AccountMoveLineInput))

    Output = ServiceRequestLine

    def mutate(self, info, id, **args):
        env = info.context["env"]
        values = env["of.service.request.line"]._prepare_mutation_values(**args)
        service_request_line = env["of.service.request.line"].search([("id", "=", id)])
        service_request_line.write(values)
        return service_request_line


class ServiceRequestLineDelete(graphene.Mutation):
    _name = "ServiceRequestLineDelete"

    class Arguments:
        id = graphene.Int(required=True)

    Output = ServiceRequestLine

    def mutate(self, info, id):
        env = info.context["env"]
        return lazy_delete(env, "of.service.request.line", id)


class ServiceRequestLineMutation(graphene.ObjectType):
    _name = "ServiceRequestLineMutation"
    _type = "mutation"

    service_request_line_create = ServiceRequestLineCreate.Field()
    service_request_line_update = ServiceRequestLineUpdate.Field()
    service_request_line_delete = ServiceRequestLineDelete.Field()
