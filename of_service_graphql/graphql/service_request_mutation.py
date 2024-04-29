import graphene

from odoo.addons.of_base_graphql.graphql.company_type import CompanyInput
from odoo.addons.of_base_graphql.graphql.employee_type import EmployeeInput
from odoo.addons.of_graphql.graphql.odoo_graphql import lazy_delete
from odoo.addons.of_graphql.graphql.user_type import UserInput
from odoo.addons.of_planning_graphql.graphql.planning_intervention_task_type import PlanningInterventionTaskInput
from odoo.addons.of_planning_graphql.graphql.planning_intervention_template_type import (
    PlanningInterventionTemplateInput,
)
from odoo.addons.of_planning_graphql.graphql.planning_intervention_type import PlanningInterventionInput

from ..graphql.attachment_type import AttachmentInput
from ..graphql.partner_type import PartnerInput
from ..graphql.service_request_line_type import ServiceRequestLineInput
from ..graphql.service_request_stage_type import ServiceRequestStageInput
from ..graphql.service_request_type_type import ServiceRequestTypeInput
from .service_request_type import ServiceRequest


class ServiceRequestCreate(graphene.Mutation):
    _name = 'ServiceRequestCreate'

    class Arguments:
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
        partner = graphene.Argument(PartnerInput)
        address = graphene.Argument(PartnerInput)
        template = graphene.Argument(PlanningInterventionTemplateInput)
        type = graphene.Argument(ServiceRequestTypeInput)
        history_interventions = graphene.List(graphene.NonNull(PlanningInterventionInput))
        task = graphene.Argument(PlanningInterventionTaskInput)
        company = graphene.Argument(CompanyInput)
        user = graphene.Argument(UserInput)
        stage = graphene.Argument(ServiceRequestStageInput)
        employees = graphene.List(graphene.NonNull(EmployeeInput))
        last_attachment = graphene.Argument(AttachmentInput)
        lines = graphene.List(graphene.NonNull(ServiceRequestLineInput))

        next_date = graphene.Date()
        end_date = graphene.Date()
        contract_end_date = graphene.Date()
        duration = graphene.Float()
        planned_duration = graphene.Float()
        remaining_duration = graphene.Float()

    Output = ServiceRequest

    def mutate(self, info, **args):
        env = info.context["env"]
        values = env['of.service.request']._prepare_mutation_values(**args)
        return env['of.service.request'].create(values)


class ServiceRequestUpdate(graphene.Mutation):
    _name = 'ServiceRequestUpdate'

    class Arguments:
        id = graphene.Int(required=True)
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
        template = graphene.Argument(PlanningInterventionTemplateInput)
        type = graphene.Argument(ServiceRequestTypeInput)
        history_interventions = graphene.List(graphene.NonNull(PlanningInterventionInput))
        task = graphene.Argument(PlanningInterventionTaskInput)
        company = graphene.Argument(CompanyInput)
        user = graphene.Argument(UserInput)
        stage = graphene.Argument(ServiceRequestStageInput)
        employees = graphene.List(graphene.NonNull(EmployeeInput))
        last_attachment = graphene.Argument(AttachmentInput)
        lines = graphene.List(graphene.NonNull(ServiceRequestLineInput))
        partner = graphene.Argument(PartnerInput)
        address = graphene.Argument(PartnerInput)
        next_date = graphene.Date()
        end_date = graphene.Date()
        contract_end_date = graphene.Date()
        duration = graphene.Float()
        planned_duration = graphene.Float()
        remaining_duration = graphene.Float()

    Output = ServiceRequest

    def mutate(self, info, id, **args):
        env = info.context["env"]
        values = env['of.service.request']._prepare_mutation_values(**args)
        service_request = env['of.service.request'].search([('id', '=', id)])
        service_request.write(values)
        return service_request


class ServiceRequestDelete(graphene.Mutation):
    _name = 'ServiceRequestDelete'

    class Arguments:
        id = graphene.Int(required=True)

    Output = ServiceRequest

    def mutate(self, info, id):
        env = info.context['env']
        return lazy_delete(env, 'of.service.request', id)


class ServiceRequestMutation(graphene.ObjectType):
    _name = 'ServiceRequestMutation'
    _type = 'mutation'

    service_request_create = ServiceRequestCreate.Field()
    service_request_update = ServiceRequestUpdate.Field()
    service_request_delete = ServiceRequestDelete.Field()
