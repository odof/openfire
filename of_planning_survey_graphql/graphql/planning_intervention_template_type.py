# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

import graphene

from odoo.addons.graphql_base import OdooObjectType
from odoo.addons.of_survey_graphql.graphql.survey_type import Survey


class PlanningInterventionTemplate(OdooObjectType):
    _name = 'PlanningInterventionTemplate'
    _type = 'types'

    survey = graphene.Field(Survey)
