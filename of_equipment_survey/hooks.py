# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).


from odoo import SUPERUSER_ID, api


def uninstall_hook(cr, registry):
    env = api.Environment(cr, SUPERUSER_ID, {})
    if planning_survey_action := env.ref("of_planning_survey.of_action_survey_form", raise_if_not_found=False):
        # Remove added part to the domain
        planning_survey_action.domain = [("survey_type", "=", "intervention_survey")]
