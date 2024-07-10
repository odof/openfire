# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import graphene

from odoo.addons.graphql_base import OdooObjectType
from odoo.addons.of_account_graphql.graphql.account_fiscal_position_type import (
    AccountFiscalPosition,
    AccountFiscalPositionInput,
)
from odoo.addons.of_base_graphql.graphql.attachment_type import Attachment, AttachmentInput
from odoo.addons.of_base_graphql.graphql.company_type import CompanyInput
from odoo.addons.of_base_graphql.graphql.employee_type import Employee, EmployeeInput
from odoo.addons.of_base_graphql.graphql.image_type import Image, ImageInput
from odoo.addons.of_base_graphql.graphql.partner_type import Partner, PartnerInput
from odoo.addons.of_graphql.graphql.company_type import Company
from odoo.addons.of_graphql.graphql.odoo_type import OdooImage
from odoo.addons.of_sale_graphql.graphql.sale_order_type import SaleOrder, SaleOrderInput
from odoo.addons.of_stock_graphql.graphql.picking_type import Picking, PickingInput

from .planning_intervention_line_type import PlanningInterventionLine, PlanningInterventionLineInput
from .planning_intervention_tag_type import PlanningInterventionTag, PlanningInterventionTagInput
from .planning_intervention_task_type import PlanningInterventionTask, PlanningInterventionTaskInput
from .planning_intervention_template_type import PlanningInterventionTemplate, PlanningInterventionTemplateInput


class PlanningIntervention(OdooObjectType):
    _name = 'PlanningIntervention'
    _type = 'types'

    id = graphene.Int(required=True)
    name = graphene.String(required=True)
    duration = graphene.Float(required=True)
    start = graphene.DateTime(required=True)
    stop = graphene.DateTime(required=True)
    of_total_duration = graphene.Float(name='totalDuration')
    of_break_duration = graphene.Float(name='breakDuration')
    of_travel_duration = graphene.Float(name='travelDuration')
    of_real_duration = graphene.Float(name='realDuration')
    of_real_start = graphene.DateTime(name='realStart')
    of_real_stop = graphene.DateTime(name='realStop')

    of_employee_ids = graphene.List(
        graphene.NonNull(Employee),
        required=True,
        description="Liste des intervenants sur l'intervention",
        name='employees',
    )
    of_is_closed = graphene.NonNull(graphene.Boolean, name='isClosed')
    company = graphene.Field(Company, required=True)
    of_state = graphene.String(required=True, name='state')
    of_picking_ids = graphene.List(graphene.NonNull(Picking), name='pickings')
    of_picking_manual_ids = graphene.List(graphene.NonNull(Picking), name='manualPickings')
    order = graphene.List(graphene.NonNull(SaleOrder))
    task = graphene.Field(PlanningInterventionTask, required=True)
    partner = graphene.Field(Partner, description="Client de l'intervention")
    address = graphene.Field(Partner, description="Adresse de l'intervention")
    attachments = graphene.List(graphene.NonNull(Attachment))
    template = graphene.Field(PlanningInterventionTemplate)
    of_internal_description = graphene.String(name='internalDescription')
    of_minutes = graphene.String(description="Compte rendu de l'intervention", name='minutes')
    description = graphene.String()
    of_customer_signature = OdooImage(name='customerSignature')
    of_operator_signature = OdooImage(name='operatorSignature')
    of_tag_ids = graphene.NonNull(graphene.List(graphene.NonNull(PlanningInterventionTag)), name='tags')
    of_line_ids = graphene.List(graphene.NonNull(PlanningInterventionLine), name='invoiceLines')
    fiscal_position = graphene.Field(AccountFiscalPosition)
    images = graphene.NonNull(graphene.List(graphene.NonNull(Image)))
    description = graphene.String(name='externalDescription')
    of_internal_description = graphene.String(name='internalDescription')

    @staticmethod
    def resolve_attachments(root, info):
        env = info.context['env']
        attachments = env['ir.attachment'].search(
            [
                ('res_model', '=', 'calendar.event'),
                ('res_id', '=', root.id),
                ('mimetype', 'in', ['image/jpeg', 'image/png', 'application/pdf']),
            ]
        )
        return attachments or []

    @staticmethod
    def resolve_company(root, info):
        return root.of_company_id

    @staticmethod
    def resolve_task(root, info):
        return root.of_task_id or None

    @staticmethod
    def resolve_order(root, info):
        return root.of_order_id

    @staticmethod
    def resolve_partner(root, info):
        return root.of_partner_id or None

    @staticmethod
    def resolve_address(root, info):
        return root.of_address_id or None

    @staticmethod
    def resolve_template(root, info):
        return root.of_template_id or None

    @staticmethod
    def resolve_fiscal_position(root, info):
        return root.of_fiscal_position_id or None

    @staticmethod
    def resolve_images(root, info):
        return root.of_all_image_ids or []


class PlanningInterventionInput(graphene.InputObjectType):
    _name = 'PlanningInterventionInput'
    _type = 'types'

    id = graphene.Int()
    name = graphene.String()
    duration = graphene.Float()
    start = graphene.DateTime()
    stop = graphene.DateTime()
    days_before_today = graphene.Int()
    days_after_today = graphene.Int()
    total_duration = graphene.Float()
    break_duration = graphene.Float()
    travel_duration = graphene.Float()
    internal_description = graphene.String()
    intervention_notes = graphene.String()
    customer_notes = graphene.String()
    customer_signature = OdooImage()
    operator_signature = OdooImage()

    employees = graphene.List(
        graphene.NonNull(EmployeeInput),
        description="Liste des intervenants sur l'intervention",
    )

    company = graphene.Field(CompanyInput)
    pickings = graphene.List(graphene.NonNull(PickingInput))
    manual_pickings = graphene.List(graphene.NonNull(PickingInput))
    order = graphene.List(graphene.NonNull(SaleOrderInput))
    task = graphene.Field(PlanningInterventionTaskInput)
    partner = graphene.Field(PartnerInput, description="Client de l'intervention")
    address = graphene.Field(PartnerInput, description="Adresse de l'intervention")
    attachments = graphene.List(graphene.NonNull(AttachmentInput))
    template = graphene.Field(PlanningInterventionTemplateInput)
    tags = graphene.List(graphene.NonNull(PlanningInterventionTagInput))
    invoice_lines = graphene.List(graphene.NonNull(PlanningInterventionLineInput))
    fiscal_position = graphene.Field(AccountFiscalPositionInput)
    images = graphene.List(graphene.NonNull(ImageInput))
    external_description = graphene.String()
    internal_description = graphene.String()
    minutes = graphene.String()


class PlanningInterventionFilterInput(PlanningInterventionInput):
    _name = 'PlanningInterventionFilterInput'
