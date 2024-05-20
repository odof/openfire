import graphene

from odoo.addons.of_graphql.graphql.odoo_domain import OdooDomainInput

from .planning_intervention_type import PlanningIntervention, PlanningInterventionFilterInput


class PlanningInterventionQuery(graphene.ObjectType):
    _name = 'PlanningInterventionQuery'
    _type = 'query'

    planning_interventions = graphene.List(
        graphene.NonNull(PlanningIntervention),
        select=graphene.Argument(PlanningInterventionFilterInput),
        domain=graphene.List(graphene.NonNull(OdooDomainInput)),
        limit=graphene.Int(),
        offset=graphene.Int(),
    )

    @staticmethod
    def resolve_planning_interventions(root, info, select=None, domain=None, offset=0, limit=10):
        env = info.context["env"]

        odoo_domain = env['calendar.event']._prepare_graphql_domain(select=select, domain=domain)

        return env['calendar.event'].search(odoo_domain, offset=offset, limit=limit)
