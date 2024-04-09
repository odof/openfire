# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

import graphene

from odoo.addons.graphql_base import OdooObjectType
from odoo.addons.of_base_graphql.graphql.attachment_type import Attachment
from odoo.addons.of_base_graphql.graphql.company_type import Company
from odoo.addons.of_base_graphql.graphql.employee_type import Employee
from odoo.addons.of_base_graphql.graphql.partner_type import Partner
from odoo.addons.of_graphql.graphql.odoo_type import OdooImage
from odoo.addons.of_sale_graphql.graphql.sale_order_type import SaleOrder
from odoo.addons.of_stock_graphql.graphql.picking_type import Picking

from .planning_intervention_tag_type import PlanningInterventionTag
from .planning_intervention_task_type import PlanningInterventionTask
from .planning_intervention_template_type import PlanningInterventionTemplate


class PlanningIntervention(OdooObjectType):
    _name = "PlanningIntervention"
    _type = "types"

    id = graphene.Int(required=True)
    name = graphene.String(required=True)
    duration = graphene.Float(required=True)
    start = graphene.DateTime(required=True)
    stop = graphene.DateTime(required=True)
    of_total_duration = graphene.Float(name='totalDuration')
    of_break_duration = graphene.Float(name='breakDuration')
    of_travel_duration = graphene.Float(name='travelDuration')
    of_employee_ids = graphene.List(
        graphene.NonNull(Employee),
        required=True,
        description="Liste des intervenants sur l'intervention",
        name='employees',
    )
    company = graphene.Field(Company, required=True)
    of_state = graphene.String(required=True, name='state')
    of_picking_ids = graphene.List(graphene.NonNull(Picking), name='pickings')
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
    of_tag_ids = graphene.List(graphene.NonNull(PlanningInterventionTag), name="tags", required=True)

    @staticmethod
    def resolve_attachments(root, info):
        env = info.context["env"]
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


class PlanningInterventionInput(graphene.InputObjectType):
    _name = "PlanningInterventionInput"
    _type = "types"

    id = graphene.Int()
    name = graphene.String()
    duration = graphene.Float()
    start = graphene.DateTime()
    stop = graphene.DateTime()
    days_before_today = graphene.Int()
    days_after_today = graphene.Int()
    of_total_duration = graphene.Float(name='totalDuration')
    of_break_duration = graphene.Float(name='breakDuration')
    of_travel_duration = graphene.Float(name='travelDuration')
    of_state = graphene.String(name='task')
    of_type = graphene.String(name='type')
    of_internal_description = graphene.String(name='internalDescription')
    of_intervention_notes = graphene.String(name='interventionNotes')
    of_customer_notes = graphene.String(name='customerNotes')
    of_customer_signature = OdooImage(name='customerSignature')
    of_operator_signature = OdooImage(name='operatorSignature')


class PlanningInterventionFilterInput(PlanningInterventionInput):
    _name = "PlanningInterventionFilterInput"


class PlanningInterventionCreateInput(PlanningInterventionInput):
    _name = "PlanningInterventionCreateInput"


class PlanningInterventionUpdateInput(PlanningInterventionInput):
    _name = "PlanningInterventionUpdateInput"
