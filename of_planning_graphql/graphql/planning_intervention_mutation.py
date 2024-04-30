import logging

import graphene

from odoo.addons.of_account_graphql.graphql.account_move_type import AccountMoveInput
from odoo.addons.of_base_graphql.graphql.attachment_type import AttachmentInput
from odoo.addons.of_base_graphql.graphql.company_type import CompanyInput
from odoo.addons.of_base_graphql.graphql.employee_type import EmployeeInput
from odoo.addons.of_base_graphql.graphql.origin_type import Origin
from odoo.addons.of_base_graphql.graphql.partner_type import PartnerInput
from odoo.addons.of_graphql.graphql.odoo_graphql import lazy_delete
from odoo.addons.of_graphql.graphql.odoo_type import OdooImage
from odoo.addons.of_sale_graphql.graphql.sale_order_type import SaleOrderInput
from odoo.addons.of_stock_graphql.graphql.picking_type import PickingInput

from .planning_intervention_line_type import PlanningInterventionLineInput
from .planning_intervention_template_type import PlanningInterventionTemplateInput
from .planning_intervention_type import PlanningIntervention

logger = logging.getLogger(__name__)


class PlanningInterventionCreate(graphene.Mutation):
    _name = 'PlanningInterventionCreate'

    class Arguments:
        name = graphene.String()
        duration = graphene.Float()
        start = graphene.DateTime()
        stop = graphene.DateTime()
        days_before_today = graphene.Int()
        days_after_today = graphene.Int()
        total_duration = graphene.Float()
        break_duration = graphene.Float()
        travel_duration = graphene.Float()
        task = graphene.String()
        type = graphene.String()
        internal_description = graphene.String()
        intervention_notes = graphene.String()
        customer_notes = graphene.String()
        customer_signature = OdooImage()
        operator_signature = OdooImage()
        partner = graphene.Argument(PartnerInput)
        invoices = graphene.List(graphene.NonNull(AccountMoveInput))
        pickings = graphene.List(graphene.NonNull(PickingInput))
        pictures = graphene.List(graphene.NonNull(AttachmentInput))
        order = graphene.Argument(SaleOrderInput)
        template = graphene.Argument(PlanningInterventionTemplateInput)
        employees = graphene.List(graphene.NonNull(EmployeeInput))
        company = graphene.Argument(CompanyInput)
        origin = graphene.Argument(Origin)
        invoice_lines = graphene.List(graphene.NonNull(PlanningInterventionLineInput))

    Output = PlanningIntervention

    def mutate(
        self,
        info,
        **args,
    ):
        env = info.context["env"]
        # ici on met origin=WEB par défaut
        if not args.get('origin', False):
            args['origin'] = 'WEB'
        values = env['calendar.event']._prepare_mutation_values(**args)
        return env['calendar.event'].create(values)


class PlanningInterventionUpdate(graphene.Mutation):
    _name = 'PlanningInterventionUpdate'

    class Arguments:
        id = graphene.Int(required=True)
        name = graphene.String()
        duration = graphene.Float()
        start = graphene.DateTime()
        stop = graphene.DateTime()
        days_before_today = graphene.Int()
        days_after_today = graphene.Int()
        total_duration = graphene.Float()
        break_duration = graphene.Float()
        travel_duration = graphene.Float()
        task = graphene.String()
        type = graphene.String()
        internal_description = graphene.String()
        intervention_notes = graphene.String()
        customer_notes = graphene.String()
        customer_signature = OdooImage()
        operator_signature = OdooImage()
        partner = graphene.Argument(PartnerInput)
        invoices = graphene.List(graphene.NonNull(AccountMoveInput))
        pickings = graphene.List(graphene.NonNull(PickingInput))
        pictures = graphene.List(graphene.NonNull(AttachmentInput))
        order = graphene.Argument(SaleOrderInput)
        template = graphene.Argument(PlanningInterventionTemplateInput)
        employees = graphene.List(graphene.NonNull(EmployeeInput))
        company = graphene.Argument(CompanyInput)
        origin = graphene.Argument(Origin)
        invoice_lines = graphene.List(graphene.NonNull(PlanningInterventionLineInput))

    Output = PlanningIntervention

    def mutate(self, info, id, **args):
        env = info.context["env"]
        # ici on met origin=WEB par défaut
        if not args.get('origin', False):
            args['origin'] = 'WEB'
        values = env['calendar.event']._prepare_mutation_values(**args)
        intervention = env['calendar.event'].search([('id', '=', id)])
        intervention.write(values)

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
