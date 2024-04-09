# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import graphene

from odoo.addons.graphql_base import OdooObjectType


class PlanningInterventionTask(OdooObjectType):
    _name = 'PlanningInterventionTask'
    _type = 'types'

    id = graphene.Int(required=True)
    name = graphene.String(required=True)
    description = graphene.String(default_value="")
    duration = graphene.Float(required=True)


class PlanningInterventionTaskInput(graphene.InputObjectType):
    _name = 'PlanningInterventionTaskInput'
    _type = 'types'

    id = graphene.Int()
    name = graphene.String()
    description = graphene.String(default_value="")
    duration = graphene.Float()


class PlanningInterventionTaskFilterInput(PlanningInterventionTaskInput):
    _name = 'PlanningInterventionTaskFilterInput'
