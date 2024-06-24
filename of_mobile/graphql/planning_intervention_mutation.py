# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

import graphene

from odoo.exceptions import AccessError

from odoo.addons.of_planning_graphql.graphql.planning_intervention_type import PlanningIntervention


class PlanningInterventionSendReport(graphene.Mutation):
    _name = 'PlanningInterventionSendReport'

    class Arguments:
        id = graphene.Int(required=True)

    Output = PlanningIntervention

    def mutate(self, info, id, **args):
        env = info.context['env']

        intervention_obj = env['calendar.event']
        intervention = intervention_obj.search([('id', '=', id)])

        if not intervention:
            raise AccessError(f"Unable to find intervention with id: {id}")

        intervention.action_send_reports_by_email()

        return intervention


class PlanningInterventionSendReportMutation(graphene.ObjectType):
    _name = 'PlanningInterventionSendReportMutation'
    _type = 'mutation'

    planning_intervention_send_report = PlanningInterventionSendReport.Field()
