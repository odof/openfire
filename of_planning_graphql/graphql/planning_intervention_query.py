import graphene
from dateutil.relativedelta import relativedelta

from odoo import fields

from odoo.addons.of_graphql.graphql.odoo_domain import OdooDomainInput
from odoo.addons.of_graphql.graphql.odoo_type import graphqlOdooDomain

from .planning_intervention_type import PlanningIntervention, PlanningInterventionFilterInput


class PlanningInterventionQuery(graphene.ObjectType):
    _name = 'PlanningInterventionQuery'
    _type = 'query'

    planning_interventions = graphene.List(
        graphene.NonNull(PlanningIntervention),
        filter=graphene.Argument(PlanningInterventionFilterInput),
        domain=graphene.List(graphene.NonNull(OdooDomainInput)),
        limit=graphene.Int(),
        offset=graphene.Int(),
    )

    @staticmethod
    def resolve_planning_interventions(root, info, filter=None, domain=None, offset=0, limit=10):
        env = info.context["env"]
        odoo_domain = []
        odoo_type = {
            'id': 'int',
            'company_id': 'int',
        }
        if domain:
            odoo_domain = graphqlOdooDomain(odoo_type, domain)

        if filter:
            today = fields.Date.from_string(fields.Date.today())

            if filter.id:
                odoo_domain += [('id', '=', filter.id)]
            if filter.name:
                odoo_domain += [('name', 'ilike', filter.name)]
            if filter.duration:
                odoo_domain += [('duration', '=', filter.duration)]
            if filter.start:
                odoo_domain += [('start', '=', filter.start)]
            if filter.stop:
                odoo_domain += [('stop', '=', filter.stop)]
            if filter.days_before_today:
                before = today + relativedelta(days=-filter.days_before_today)
                odoo_domain += [('start', '>=', fields.Date.to_string(before))]
            if filter.days_after_today:
                after = today + relativedelta(days=-filter.days_after_today)
                odoo_domain += [('start', '>=', fields.Date.to_string(after))]
            odoo_domain += [('of_state', 'not in', ['cancel', 'postponed']), ('of_type', '=', 'intervention')]

        return env["calendar.event"].search(odoo_domain, offset=offset, limit=limit)
