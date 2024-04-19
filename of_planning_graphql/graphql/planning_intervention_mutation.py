import logging

import graphene

from odoo.addons.of_account_graphql.graphql.account_move_mutation import AccountMoveCreate, AccountMoveUpdate
from odoo.addons.of_account_graphql.graphql.account_move_type import AccountMoveInput
from odoo.addons.of_base_graphql.graphql.attachment_mutation import AttachmentCreate, AttachmentUpdate, convertImage
from odoo.addons.of_base_graphql.graphql.attachment_type import AttachmentInput
from odoo.addons.of_base_graphql.graphql.company_mutation import CompanyCreate, CompanyUpdate
from odoo.addons.of_base_graphql.graphql.company_type import CompanyInput
from odoo.addons.of_base_graphql.graphql.employee_mutation import EmployeeCreate, EmployeeUpdate
from odoo.addons.of_base_graphql.graphql.employee_type import EmployeeInput
from odoo.addons.of_base_graphql.graphql.origin_type import Origin
from odoo.addons.of_base_graphql.graphql.partner_mutation import PartnerCreate, PartnerUpdate
from odoo.addons.of_base_graphql.graphql.partner_type import PartnerInput
from odoo.addons.of_graphql.graphql.odoo_graphql import lazy_create, lazy_delete, lazy_update
from odoo.addons.of_sale_graphql.graphql.sale_order_mutation import SaleOrderCreate, SaleOrderUpdate
from odoo.addons.of_sale_graphql.graphql.sale_order_type import SaleOrderInput
from odoo.addons.of_stock_graphql.graphql.picking_mutation import PickingCreate, PickingUpdate
from odoo.addons.of_stock_graphql.graphql.picking_type import PickingInput

from .planning_intervention_template_mutation import (
    PlanningInterventionTemplateCreate,
    PlanningInterventionTemplateUpdate,
)
from .planning_intervention_template_type import PlanningInterventionTemplateInput
from .planning_intervention_type import (
    PlanningIntervention,
    PlanningInterventionCreateInput,
    PlanningInterventionUpdateInput,
)

logger = logging.getLogger(__name__)


class PlanningInterventionCreate(graphene.Mutation):
    _name = 'PlanningInterventionCreate'

    class Arguments:
        input = PlanningInterventionCreateInput(required=True)
        partner = PartnerInput()
        invoices = graphene.List(graphene.NonNull(AccountMoveInput))
        pickings = graphene.List(graphene.NonNull(PickingInput))
        pictures = graphene.List(graphene.NonNull(AttachmentInput))
        order = SaleOrderInput()
        template = PlanningInterventionTemplateInput()
        employees = graphene.List(graphene.NonNull(EmployeeInput))
        company = CompanyInput()
        origin = Origin()

    Output = PlanningIntervention

    def mutate(
        self,
        info,
        input,
        partner=None,
        invoices=None,
        pickings=None,
        pictures=None,
        order=None,
        template=None,
        employees=None,
        company=None,
        origin='WEB',
    ):
        env = info.context["env"]

        # Les données qui viennent de cet input (dans datas) doivent être modifiées avant d'être
        # importé dans odoo, donc on convertit à la volée
        if attachment := input.get("of_customer_signature", False):
            input.of_customer_signature = convertImage(attachment)

        if attachment := input.get("of_operator_signature", False):
            input.of_operator_signature = convertImage(attachment)

        create_invoices = env['account.move']
        create_pickings = env['stock.picking']
        create_pictures = env['ir.attachment']
        create_employees = env['hr.employee']

        if origin == "MOBILE":
            input['of_force_dates'] = True
            input['name'] = ''
            input['user_id'] = env.user.id
            input['last_updated_mobile'] = True

        if partner:
            if partner.id:
                partner = PartnerUpdate().mutate(info, id=partner.id, input=partner)
            else:
                partner = PartnerCreate().mutate(info, input=partner)

        if invoices:
            for invoice in invoices:
                if invoice.id:
                    invoice = AccountMoveUpdate().mutate(info, id=invoice.id, input=invoice)
                else:
                    invoice = AccountMoveCreate().mutate(info, input=invoice)
                create_invoices += invoice

        if pickings:
            for picking in pickings:
                if picking.id:
                    picking = PickingUpdate().mutate(info, id=picking.id, input=picking)
                else:
                    picking = PickingCreate().mutate(info, input=picking)
                create_pickings += picking

        if pictures:
            for picture in pictures:
                if picture.id:
                    picture = AttachmentUpdate().mutate(info, id=picture.id, input=picture)
                else:
                    picture = AttachmentCreate().mutate(info, input=picture)
                create_pictures += picture

        if order:
            if order.id:
                order = SaleOrderUpdate().mutate(info, id=order.id, input=order)
            else:
                order = SaleOrderCreate().mutate(info, input=order)

        if template:
            if template.id:
                template = PlanningInterventionTemplateUpdate().mutate(info, id=template.id, input=template)
            else:
                template = PlanningInterventionTemplateCreate().mutate(info, input=template)

        if employees:
            for employee in employees:
                if employee.id:
                    employee = EmployeeUpdate().mutate(info, id=employee.id, input=employee)
                else:
                    employee = EmployeeCreate().mutate(info, input=employee)
                create_employees += employee

        if company:
            if company.id:
                company = CompanyUpdate().mutate(info, id=company.id, input=company)
            else:
                company = CompanyCreate().mutate(info, input=company)

        intervention = lazy_create(env, 'calendar.event', input)

        if partner:
            intervention.of_partner_id = partner

        if invoices:
            intervention.of_invoice_ids = [(6, 0, create_invoices.ids)]

        if pickings:
            intervention.picking_ids = [(6, 0, create_pickings.ids)]

        if pictures:
            intervention.of_all_image_ids = [(6, 0, create_pictures.ids)]

        if order:
            intervention.of_order_id = order

        if template:
            intervention.template_id = template

        if employees:
            intervention.employee_ids = [(6, 0, create_employees.ids)]

        if company:
            intervention.of_company_id = company

        return intervention


class PlanningInterventionUpdate(graphene.Mutation):
    _name = 'PlanningInterventionUpdate'

    class Arguments:
        id = graphene.Int(required=True)
        input = PlanningInterventionUpdateInput(required=True)
        partner = PartnerInput()
        invoices = graphene.List(graphene.NonNull(AccountMoveInput))
        pickings = graphene.List(graphene.NonNull(PickingInput))
        pictures = graphene.List(graphene.NonNull(AttachmentInput))
        order = SaleOrderInput()
        template = PlanningInterventionTemplateInput()
        employees = graphene.List(graphene.NonNull(EmployeeInput))
        company = CompanyInput()
        origin = Origin()

    Output = PlanningIntervention

    def mutate(
        self,
        info,
        id,
        input,
        partner=None,
        invoices=None,
        pickings=None,
        pictures=None,
        order=None,
        template=None,
        employees=None,
        company=None,
        service_request=None,
        origin="WEB",
    ):
        env = info.context["env"]

        # Les données qui viennent de cet input (dans datas) doivent être modifiées avant d'être
        # importé dans odoo, donc on convertit à la volée
        if attachment := input.get("of_customer_signature", False):
            input.of_customer_signature = convertImage(attachment)

        if attachment := input.get("of_operator_signature", False):
            input.of_operator_signature = convertImage(attachment)

        update_invoices = env['account.move']
        update_pickings = env['stock.picking']
        update_pictures = env['ir.attachment']
        update_employees = env['hr.employee']

        if partner:
            if partner.id:
                partner = PartnerUpdate().mutate(info, id=partner.id, input=partner)
            else:
                partner = PartnerCreate().mutate(info, input=partner)

        if invoices:
            for invoice in invoices:
                if invoice.id:
                    invoice = AccountMoveUpdate().mutate(info, id=invoice.id, input=invoice)
                else:
                    invoice = AccountMoveCreate().mutate(info, input=invoice)
                update_invoices += invoice

        if pickings:
            for picking in pickings:
                if pickings.id:
                    picking = PickingUpdate().mutate(info, id=picking.id, input=picking)
                else:
                    invoice = PickingCreate().mutate(info, input=picking)
                update_pickings += picking

        if pictures:
            for picture in pictures:
                if picture.id:
                    picture = AttachmentUpdate().mutate(info, id=picture.id, input=picture)
                else:
                    invoice = AttachmentCreate().mutate(info, input=picture)
                update_pictures += picture

        if order:
            if order.id:
                order = SaleOrderUpdate().mutate(info, id=order.id, input=order)
            else:
                order = SaleOrderCreate().mutate(info, input=order)

        if template:
            if template.id:
                template = PlanningInterventionTemplateUpdate().mutate(info, id=template.id, input=template)
            else:
                template = PlanningInterventionTemplateCreate().mutate(info, input=template)

        if employees:
            for employee in employees:
                if employee.id:
                    employee = EmployeeUpdate().mutate(info, id=employee.id, input=employee)
                else:
                    employee = EmployeeCreate().mutate(info, input=employee)
                update_employees += employee

        if company:
            if company.id:
                company = CompanyUpdate().mutate(info, id=company.id, input=company)
            else:
                company = CompanyCreate().mutate(info, input=company)

        intervention = lazy_update(env, 'calendar.event', id, input)

        if partner:
            intervention.of_partner_id = partner

        if invoices:
            intervention.of_invoice_ids = [(6, 0, update_invoices.ids)]

        if pickings:
            intervention.picking_ids = [(6, 0, update_pickings.ids)]

        if pictures:
            intervention.of_all_image_ids = [(6, 0, update_pictures.ids)]

        if order:
            intervention.of_order_id = order

        if template:
            intervention.template_id = template

        if employees:
            intervention.employee_ids = [(6, 0, update_employees.ids)]

        if company:
            intervention.of_company_id = company

        return intervention


class PlanningInterventionDelete(graphene.Mutation):
    _name = 'PlanningInterventionDelete'

    class Arguments:
        id = graphene.Int(required=True)

    Output = PlanningIntervention

    def mutate(self, info, id):
        env = info.context['env']

        return lazy_delete(env, 'calendar.event', id)


class PlanningInterventionMutation(graphene.ObjectType):
    _name = 'PlanningInterventionMutation'
    _type = 'mutation'

    planning_intervention_update = PlanningInterventionUpdate.Field()
    planning_intervention_create = PlanningInterventionCreate.Field()
    planning_intervention_delete = PlanningInterventionDelete.Field()
