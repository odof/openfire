# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

import graphene

from odoo.addons.graphql_base import OdooObjectType
from odoo.addons.of_base_graphql.graphql.company_type import CompanyInput
from odoo.addons.of_base_graphql.graphql.employee_type import Employee, EmployeeInput
from odoo.addons.of_graphql.graphql.company_type import Company
from odoo.addons.of_graphql.graphql.user_type import User, UserInput
from odoo.addons.of_planning_graphql.graphql.planning_intervention_task_type import (
    PlanningInterventionTask,
    PlanningInterventionTaskInput,
)
from odoo.addons.of_planning_graphql.graphql.planning_intervention_template_type import (
    PlanningInterventionTemplate,
    PlanningInterventionTemplateInput,
)
from odoo.addons.of_planning_graphql.graphql.planning_intervention_type import (
    PlanningIntervention,
    PlanningInterventionInput,
)

from ..graphql.attachment_type import Attachment, AttachmentInput
from ..graphql.partner_type import Partner, PartnerInput
from ..graphql.service_request_line_type import ServiceRequestLine, ServiceRequestLineInput
from ..graphql.service_request_stage_type import ServiceRequestStage, ServiceRequestStageInput
from ..graphql.service_request_type_type import ServiceRequestType, ServiceRequestTypeInput


class AffectationType(graphene.Enum):
    MINE = "mine"
    ALL = "all"
    NOT_AFFECTED = "not_affected"


class PeriodType(graphene.Enum):
    CURRENT_WEEK = "current_week"
    NEXT_WEEK = "next_week"
    CURRENT_MONTH = "current_month"


class SortType(graphene.Enum):
    NEAREST_END_DATE = "nearest_end_date"
    NEAREST_DISTANCE = "nearest_distance"


class ServiceRequest(OdooObjectType):
    _name = "ServiceRequest"
    _type = "types"

    id = graphene.Int(required=True)
    name = graphene.String()
    active = graphene.Boolean()
    origin = graphene.String()
    number = graphene.String()
    title = graphene.String()
    priority = graphene.String()
    request_label_date = graphene.String(name="date")
    state = graphene.String(name="planningStatus")
    base_state = graphene.String(name="calculationStatus")
    state_punctual = graphene.String(name="state")
    intervention_ids = graphene.List(graphene.NonNull(PlanningIntervention), name='interventions')
    intervention_count = graphene.Int()
    template = graphene.Field(PlanningInterventionTemplate)
    type = graphene.Field(ServiceRequestType)
    history_intervention_ids = graphene.List(graphene.NonNull(PlanningIntervention), name='historyInterventions')
    task = graphene.Field(PlanningInterventionTask, required=True)
    company = graphene.Field(Company, required=True)
    user = graphene.Field(User)
    stage = graphene.Field(ServiceRequestStage)
    employee_ids = graphene.List(graphene.NonNull(Employee), name='employees')
    last_attachment = graphene.Field(Attachment)
    line_ids = graphene.List(graphene.NonNull(ServiceRequestLine), name='lines')
    partner = graphene.Field(Partner, required=True)
    address = graphene.Field(Partner)
    next_date = graphene.Date()
    end_date = graphene.Date()
    contract_end_date = graphene.Date()
    duration = graphene.Float()
    planned_duration = graphene.Float()
    remaining_duration = graphene.Float()
    note = graphene.String()

    @staticmethod
    def resolve_template(root, info):
        return root.template_id or None

    @staticmethod
    def resolve_type(root, info):
        return root.type_id or None

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
    date = graphene.String()
    planning_status = graphene.String()
    calculation_status = graphene.String()
    state = graphene.String()
    interventions = graphene.List(graphene.NonNull(PlanningInterventionInput))
    intervention_count = graphene.Int()
    template = graphene.Field(PlanningInterventionTemplateInput)
    type = graphene.Field(ServiceRequestTypeInput)
    history_interventions = graphene.List(graphene.NonNull(PlanningInterventionInput))
    task = graphene.Field(PlanningInterventionTaskInput)
    company = graphene.Field(CompanyInput)
    user = graphene.Field(UserInput)
    stage = graphene.Field(ServiceRequestStageInput)
    employees = graphene.List(graphene.NonNull(EmployeeInput))
    last_attachment = graphene.Field(AttachmentInput)
    lines = graphene.List(graphene.NonNull(ServiceRequestLineInput))
    partner = graphene.Field(PartnerInput)
    address = graphene.Field(PartnerInput)
    next_date = graphene.Date()
    end_date = graphene.Date()
    contract_end_date = graphene.Date()
    duration = graphene.Float()
    planned_duration = graphene.Float()
    remaining_duration = graphene.Float()


class ServiceRequestFilterInput(ServiceRequestInput):
    _name = "ServiceRequestFilterInput"
    affectation = graphene.Field(AffectationType)
    period = graphene.Field(PeriodType)
    latitude = graphene.Float()
    longitude = graphene.Float()
    max_distance = graphene.Float()
    sort = graphene.Field(SortType)
