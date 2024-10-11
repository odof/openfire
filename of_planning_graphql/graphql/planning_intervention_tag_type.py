# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import graphene

from odoo.addons.graphql_base import OdooObjectType


class PlanningInterventionTag(OdooObjectType):
    _name = "PlanningInterventionTag"
    _type = "types"

    id = graphene.Int(required=True)
    name = graphene.String(required=True)
    sequence = graphene.Int()
    active = graphene.Boolean()
    color = graphene.Int()
    color_value = graphene.String(required=True, description="Valeur de la couleur associée au tag")

    def resolve_color_value(root, info):
        color = {
            0: "#4D4D4D",
            1: "#61BD4F",
            2: "#F2D600",
            3: "#FFAB4A",
            4: "#EB5A46",
            5: "#875A7B",
            6: "#0079BF",
            7: "#00C2E0",
            8: "#4CD98E",
            9: "#FF80CE",
            10: "#B6BBBF",
        }

        return color[root.color if root.color in color else 0]


class PlanningInterventionTagInput(graphene.InputObjectType):
    _name = "PlanningInterventionTagInput"
    _type = "types"

    id = graphene.Int()
    name = graphene.String()
    sequence = graphene.Int()
    active = graphene.Boolean()
    color = graphene.Int()


class PlanningInterventionTagFilterInput(PlanningInterventionTagInput):
    _name = "PlanningInterventionTagFilterInput"
