# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import graphene

from odoo.addons.graphql_base import OdooObjectType

from .planning_intervention_template_type import PlanningInterventionTemplate


class Company(OdooObjectType):
    _name = 'Company'
    _type = 'types'

    default_intervention_template = graphene.Field(PlanningInterventionTemplate)
    intervention_template_mandatory = graphene.Boolean()

    @staticmethod
    def resolve_default_intervention_template(root, info):
        return root.of_default_intervention_template_id or None

    @staticmethod
    def resolve_intervention_template_mandatory(root, info):
        return root.of_is_intervention_template_required
