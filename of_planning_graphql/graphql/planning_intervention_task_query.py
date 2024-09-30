# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import graphene

from odoo.addons.of_graphql.graphql.odoo_domain import OdooDomainInput

from .planning_intervention_task_type import PlanningInterventionTask, PlanningInterventionTaskFilterInput


class PlanningInterventionTaskQuery(graphene.ObjectType):
    _name = "PlanningInterventionTaskQuery"
    _type = "query"

    planning_tasks = graphene.List(
        graphene.NonNull(PlanningInterventionTask),
        select=graphene.Argument(PlanningInterventionTaskFilterInput),
        domain=graphene.List(graphene.NonNull(OdooDomainInput)),
        limit=graphene.Int(),
        offset=graphene.Int(),
    )

    @staticmethod
    def resolve_planning_tasks(root, info, select=None, domain=None, offset=0, limit=10):
        env = info.context["env"]
        odoo_domain = env["of.planning.task"]._prepare_graphql_domain(select=select, domain=domain)

        return env["of.planning.task"].search(odoo_domain, offset=offset, limit=limit)
