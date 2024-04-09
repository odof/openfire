# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

import graphene

from odoo.addons.graphql_base import OdooObjectType
from odoo.addons.of_base_graphql.graphql.company_type import Company
from odoo.addons.of_base_graphql.graphql.employee_type import Employee
from odoo.addons.of_graphql.graphql.user_type import User
from odoo.addons.of_planning_graphql.graphql.planning_intervention_task_type import PlanningInterventionTask
from odoo.addons.of_planning_graphql.graphql.planning_intervention_template_type import PlanningInterventionTemplate
from odoo.addons.of_planning_graphql.graphql.planning_intervention_type import PlanningIntervention

from ..graphql.attachment_type import Attachment
from ..graphql.partner_type import Partner
from ..graphql.service_request_line_type import ServiceRequestLine
from ..graphql.service_request_stage_type import ServiceRequestStage
from ..graphql.service_request_type_type import ServiceRequestType


class ServiceRequest(OdooObjectType):
    _name = "ServiceRequest"
    _type = "types"

    id = graphene.Int()
    name = graphene.String()
    active = graphene.Boolean()
    origin = graphene.String()
    number = graphene.String()
    title = graphene.String()
    priority = graphene.String()
    request_label_date = graphene.String(name="date")
    state = graphene.String(name="planning_status")
    base_state = graphene.String(name="calculation_status")
    state_punctual = graphene.String(name="state")
    intervention_ids = graphene.List(graphene.NonNull(PlanningIntervention))
    intervention_count = graphene.Int()
    template = graphene.Field(PlanningInterventionTemplate)
    type = graphene.Field(ServiceRequestType)
    history_intervention_ids = graphene.List(graphene.NonNull(PlanningIntervention), name='history_interventions')
    task = graphene.Field(PlanningInterventionTask)
    company = graphene.Field(Company)
    user = graphene.Field(User)
    stage = graphene.Field(ServiceRequestStage)
    employee_ids = graphene.List(graphene.NonNull(Employee))
    last_attachment = graphene.Field(Attachment)
    line_ids = graphene.List(graphene.NonNull(ServiceRequestLine), name='lines')
    partner = graphene.Field(Partner)
    address = graphene.Field(Partner)
    next_date = graphene.Date()
    end_date = graphene.Date()
    contract_end_date = graphene.Date()
    duration = graphene.Float()
    planned_duration = graphene.Float()
    remaining_duration = graphene.Float()

    @staticmethod
    def resolve_template(root, info):
        return root.template_id or None

    @staticmethod
    def resolve_type(root, info):
        return root.of_type or None

    @staticmethod
    def resolve_task(root, info):
        return root.task_id or None

    @staticmethod
    def resolve_company(root, info):
        return root.company_id or None

    @staticmethod
    def resolve_user(root, info):
        return root.user_id or None

    @staticmethod
    def resolve_stage(root, info):
        return root.stage_id or None

    @staticmethod
    def resolve_last_attachment(root, info):
        return root.last_attachment_id or None

    @staticmethod
    def resolve_partner(root, info):
        return root.partner_id or None

    @staticmethod
    def resolve_address(root, info):
        return root.address_id or None


class ServiceRequestInput(graphene.InputObjectType):
    _name = "ServiceRequestInput"
    _type = "types"

    id = graphene.Int()
    name = graphene.String()
    active = graphene.Boolean()
    origin = graphene.String()
    number = graphene.String()
    title = graphene.String()
    priority = graphene.String()
    request_label_date = graphene.String(name="date")
    state = graphene.String(name="planning_status")
    base_state = graphene.String(name="calculation_status")
    state_punctual = graphene.String(name="state")
    next_date = graphene.Date()
    end_date = graphene.Date()
    contract_end_date = graphene.Date()
    duration = graphene.Float()
    planned_duration = graphene.Float()
    remaining_duration = graphene.Float()


class ServiceRequestFilterInput(ServiceRequestInput):
    _name = "ServiceRequestFilterInput"


class ServiceRequestCreateInput(ServiceRequestInput):
    _name = "ServiceRequestCreateInput"


class ServiceRequestUpdateInput(ServiceRequestInput):
    _name = "ServiceRequestUpdateInput"
