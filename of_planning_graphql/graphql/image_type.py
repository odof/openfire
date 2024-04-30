# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

import graphene

from odoo.addons.graphql_base import OdooObjectType

from .planning_intervention_type import PlanningIntervention


class Image(OdooObjectType):
    _name = 'Image'
    _type = 'types'

    intervention_id = graphene.Field(PlanningIntervention, name='intervention')
    intervention_date = graphene.DateTime()
    intervention_status = graphene.String()

    @staticmethod
    def resolve_intervention(root, info):
        return root.intervention_id or None
