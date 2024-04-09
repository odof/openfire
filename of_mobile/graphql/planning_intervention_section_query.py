# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

import graphene

from odoo.addons.of_graphql.graphql.odoo_domain import OdooDomainInput

from .planning_intervention_section_type import PlanningInterventionSection, PlanningInterventionSectionFilterInput


class PlanningInterventionSectionQuery(graphene.ObjectType):
    _name = 'PlanningInterventionSectionQuery'
    _type = 'query'

    planning_intervention_sections = graphene.List(
        graphene.NonNull(PlanningInterventionSection),
        select=graphene.Argument(PlanningInterventionSectionFilterInput),
        domain=graphene.List(graphene.NonNull(OdooDomainInput)),
        limit=graphene.Int(),
        offset=graphene.Int(),
    )

    @staticmethod
    def resolve_planning_intervention_sections(root, info, select=None, domain=None, offset=0, limit=10):
        env = info.context['env']
        odoo_domain = env['of.planning.intervention.section']._prepare_graphql_domain(select=select, domain=domain)

        return env['of.planning.intervention.section'].search(odoo_domain, offset=offset, limit=limit)
