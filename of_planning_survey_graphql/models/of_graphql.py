# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import graphene

from odoo import models

from odoo.addons.of_graphql.graphql.odoo_graphql import OdooGraphql
from odoo.addons.of_survey_graphql.graphql.survey_type import SurveyInput
from odoo.addons.of_survey_graphql.graphql.survey_user_input_type import SurveyUserInputInput

from ..graphql.planning_intervention_template_type import PlanningInterventionTemplate
from ..graphql.planning_intervention_type import PlanningIntervention


class OFGraphql(models.AbstractModel):
    _inherit = 'of.graphql'

    def _of_planning_survey_graphql_register(self, dbname):
        # ici on charge le graphql de ce module
        OdooGraphql.add(
            dbname,
            [
                PlanningIntervention,
                PlanningInterventionTemplate,
            ],
        )

    def _prepare_arguments(self):
        arguments = super()._prepare_arguments()

        new_arguments = {
            "PlanningInterventionMutation": {
                "planning_intervention_create": {
                    "survey": SurveyInput,
                    "survey_user_inputs": graphene.List(SurveyUserInputInput),
                },
                "planning_intervention_update": {
                    "survey": SurveyInput,
                    "survey_user_inputs": graphene.List(SurveyUserInputInput),
                },
            }
        }
        arguments = self._add_arguments(new_arguments, arguments)

        return arguments
