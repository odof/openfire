# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

import graphene

from odoo.addons.of_graphql.graphql.odoo_domain import OdooDomainInput

from .planning_intervention_template_type import PlanningInterventionTemplate, PlanningInterventionTemplateFilterInput


class PlanningInterventionTemplateQuery(graphene.ObjectType):
    _name = 'PlanningInterventionTemplateQuery'
    _type = 'query'

    planning_intervention_templates = graphene.List(
        graphene.NonNull(PlanningInterventionTemplate),
        select=graphene.Argument(PlanningInterventionTemplateFilterInput),
        domain=graphene.List(graphene.NonNull(OdooDomainInput)),
        limit=graphene.Int(),
        offset=graphene.Int(),
    )

    @staticmethod
    def resolve_planning_intervention_templates(root, info, select=None, domain=None, offset=0, limit=10):
        env = info.context['env']
        odoo_domain = env['of.planning.intervention.template']._prepare_graphql_domain(select=select, domain=domain)

        return env['of.planning.intervention.template'].search(odoo_domain, offset=offset, limit=limit)
