# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import graphene

from odoo.addons.graphql_base import OdooObjectType


class PlanningInterventionTask(OdooObjectType):
    _name = 'PlanningInterventionTask'
    _type = 'types'

    mobile = graphene.Boolean()


class PlanningInterventionTaskInput(graphene.InputObjectType):
    _name = 'PlanningInterventionTaskInput'
    _type = 'types'

    mobile = graphene.Boolean()


class PlanningInterventionTaskFilterInput(PlanningInterventionTaskInput):
    _name = 'PlanningInterventionTaskFilterInput'
