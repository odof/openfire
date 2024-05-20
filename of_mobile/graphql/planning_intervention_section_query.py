# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

import graphene

from odoo.addons.of_graphql.graphql.odoo_domain import OdooDomainInput
from odoo.addons.of_graphql.graphql.odoo_type import graphqlOdooDomain

from .planning_intervention_section_type import PlanningInterventionSection, PlanningInterventionSectionFilterInput


class PlanningInterventionSectionQuery(graphene.ObjectType):
    _name = 'PlanningInterventionSectionQuery'
    _type = 'query'

    planning_intervention_sections = graphene.List(
        graphene.NonNull(PlanningInterventionSection),
        filter=graphene.Argument(PlanningInterventionSectionFilterInput),
        domain=graphene.List(graphene.NonNull(OdooDomainInput)),
        limit=graphene.Int(),
        offset=graphene.Int(),
    )

    @staticmethod
    def resolve_planning_intervention_sections(root, info, filter=None, domain=None, offset=0, limit=10):
        env = info.context["env"]
        odoo_type = {
            'id': 'int',
        }
        odoo_domain = graphqlOdooDomain(odoo_type, domain) if domain else []
        if filter:
            if filter.id:
                odoo_domain += [('id', '=', filter.id)]
            if filter.name:
                odoo_domain += [('name', 'like', filter.name)]

        return env['of.planning.intervention.section'].search(odoo_domain, offset=offset, limit=limit)
