# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

import graphene

from odoo.addons.of_graphql.graphql.odoo_domain import OdooDomainInput

from .planning_intervention_tag_type import PlanningInterventionTag, PlanningInterventionTagFilterInput


class PlanningInterventionTagQuery(graphene.ObjectType):
    _name = 'PlanningInterventionTagQuery'
    _type = 'query'

    planning_intervention_tags = graphene.List(
        graphene.NonNull(PlanningInterventionTag),
        select=graphene.Argument(PlanningInterventionTagFilterInput),
        domain=graphene.List(graphene.NonNull(OdooDomainInput)),
        limit=graphene.Int(),
        offset=graphene.Int(),
    )

    @staticmethod
    def resolve_planning_intervention_tags(root, info, select=None, domain=None, offset=0, limit=10):
        env = info.context['env']
        odoo_domain = env['of.planning.tag']._prepare_graphql_domain(select=select, domain=domain)

        return env['of.planning.tag'].search(odoo_domain, offset=offset, limit=limit)
