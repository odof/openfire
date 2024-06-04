# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

import graphene

from odoo import fields
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

        try:
            email_template = env.ref("of_planning.email_template_of_planning_intervention_report")
        except Exception:
            raise AccessError("Unable to find email template")

        if env.user.email:
            email_template = env.ref("of_planning.email_template_of_planning_intervention_report").with_context(
                default_email_from=env.user.email_formatted
            )
            email_template.with_context(force_attachment=True).send_mail(intervention.id, force_send=True)
            intervention.of_mobile_report_send_date = fields.Datetime.now()

        return intervention


class PlanningInterventionSendReportMutation(graphene.ObjectType):
    _name = 'PlanningInterventionSendReportMutation'
    _type = 'mutation'

    planning_intervention_send_report = PlanningInterventionSendReport.Field()
