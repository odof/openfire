# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import graphene

from odoo.addons.graphql_base import OdooObjectType


class PlanningInterventionSection(OdooObjectType):
    _name = 'PlanningInterventionSection'
    _type = 'types'

    id = graphene.Int(required=True)
    name = graphene.String(required=True)
    ttype = graphene.String(required=True, name='type')


class PlanningInterventionSectionInput(graphene.InputObjectType):
    _name = 'PlanningInterventionSectionInput'
    _type = 'types'

    id = graphene.Int()
    name = graphene.String()
    type = graphene.String()


class PlanningInterventionSectionFilterInput(PlanningInterventionSectionInput):
    _name = 'PlanningInterventionSectionFilterInput'
