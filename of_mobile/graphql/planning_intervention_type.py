# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

import graphene

from odoo.addons.graphql_base import OdooObjectType
from odoo.addons.of_equipment_graphql.graphql.equipment_type import Equipment
from odoo.addons.of_survey_graphql.graphql.survey_user_input_type import SurveyUserInput

from .planning_intervention_section_type import PlanningInterventionSection


class PlanningIntervention(OdooObjectType):
    _name = 'PlanningIntervention'
    _type = 'types'

    update_date = graphene.DateTime()
    equipments = graphene.NonNull(graphene.List(graphene.NonNull(Equipment)))
    historical = graphene.NonNull(graphene.List(graphene.NonNull(lambda: PlanningIntervention)))
    comings = graphene.NonNull(graphene.List(graphene.NonNull(lambda: PlanningIntervention)))
    survey_user_input = graphene.Field(SurveyUserInput)
    of_section_to_display_ids = graphene.NonNull(
        graphene.List(graphene.NonNull(lambda: PlanningInterventionSection)), name='sections'
    )

    @staticmethod
    def resolve_update_date(root, info):
        return root.of_update_date or None

    @staticmethod
    def resolve_equipments(root, info):
        return root.of_equipment_ids or []

    @staticmethod
    def resolve_historical(root, info):
        return root.of_historical_ids or []

    @staticmethod
    def resolve_comings(root, info):
        return root.of_coming_ids or []

    @staticmethod
    def resolve_survey_user_input(root, info):
        return root.of_survey_user_input or None

    def resolve_sections(root, info):
        return root.of_section_to_display_ids or []


class PlanningInterventionsOffline(graphene.ObjectType):
    _name = 'PlanningInterventionsOffline'
    _type = 'types'

    interventions = graphene.List(
        graphene.NonNull(PlanningIntervention),
        required=True,
    )
    interventions_to_delete = graphene.List(
        graphene.NonNull(graphene.Int),
        required=True,
    )
