# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import graphene

from odoo.addons.graphql_base import OdooObjectType

from .planning_intervention_type import PlanningIntervention, PlanningInterventionInput


class Image(OdooObjectType):
    _name = "Image"
    _type = "types"

    intervention_id = graphene.Field(PlanningIntervention, name="intervention")
    intervention_date = graphene.DateTime()
    intervention_status = graphene.String()

    @staticmethod
    def resolve_intervention(root, info):
        return root.intervention_id or None


class ImageInput(graphene.InputObjectType):
    _name = "ImageInput"
    _type = "types"

    intervention = graphene.Field(PlanningInterventionInput)
    intervention_date = graphene.DateTime()
    intervention_status = graphene.String()
