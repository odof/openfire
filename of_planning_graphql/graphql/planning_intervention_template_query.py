# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

import graphene

from odoo.addons.of_graphql.graphql.odoo_domain import OdooDomainInput
from odoo.addons.of_graphql.graphql.odoo_type import graphqlOdooDomain

from .planning_intervention_template_type import PlanningInterventionTemplate, PlanningInterventionTemplateFilterInput


class PlanningInterventionTemplateQuery(graphene.ObjectType):
    _name = "PlanningInterventionTemplateQuery"
    _type = "query"

    planning_intervention_templates = graphene.List(
        graphene.NonNull(PlanningInterventionTemplate),
        filter=graphene.Argument(PlanningInterventionTemplateFilterInput),
        domain=graphene.List(graphene.NonNull(OdooDomainInput)),
        limit=graphene.Int(),
        offset=graphene.Int(),
    )

    @staticmethod
    def resolve_planning_intervention_templates(root, info, filter=None, domain=None, offset=0, limit=1):
        env = info.context['env']
        odoo_domain = []
        odoo_type = {
            'id': 'int',
            'company_id': 'int',
            'is_default_template': 'boolean',
        }
        if domain:
            odoo_domain = graphqlOdooDomain(odoo_type, domain)

        if filter:
            if filter.id:
                odoo_domain += [('id', '=', filter.id)]
            if filter.name:
                odoo_domain += [('name', 'ilike', filter.name)]
            if filter.is_default_template:
                odoo_domain += [('is_default_template', '=', filter.is_default_template)]

        return env['of.planning.intervention.template'].search(odoo_domain, offset=offset, limit=limit)
