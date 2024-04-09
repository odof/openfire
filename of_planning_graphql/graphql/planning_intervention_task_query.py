import graphene

from odoo.addons.of_graphql.graphql.odoo_domain import OdooDomainInput
from odoo.addons.of_graphql.graphql.odoo_type import graphqlOdooDomain

from .planning_intervention_task_type import PlanningInterventionTask, PlanningInterventionTaskFilterInput


class PlanningInterventionTaskQuery(graphene.ObjectType):
    _name = 'PlanningInterventionTaskQuery'
    _type = "query"

    planning_tasks = graphene.List(
        graphene.NonNull(PlanningInterventionTask),
        filter=graphene.Argument(PlanningInterventionTaskFilterInput),
        domain=graphene.List(graphene.NonNull(OdooDomainInput)),
        limit=graphene.Int(),
        offset=graphene.Int(),
    )

    @staticmethod
    def resolve_planning_tasks(root, info, filter=None, domain=None, offset=0, limit=10):
        env = info.context['env']
        odoo_domain = []
        odoo_type = {
            'id': 'int',
            'company_id': 'int',
            'duration': 'float',
        }
        if domain:
            odoo_domain = graphqlOdooDomain(odoo_type, domain)

        if filter:
            if filter.id:
                odoo_domain += [('id', '=', filter.id)]
            if filter.name:
                odoo_domain += [('name', 'ilike', filter.name)]
            if filter.duration:
                odoo_domain += [('duration', '=', filter.duration)]

        return env['of.planning.task'].search(odoo_domain, offset=offset, limit=limit)
