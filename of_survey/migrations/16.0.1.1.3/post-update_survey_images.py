# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import SUPERUSER_ID, api


def _update_survey_images(cr, env):
    """Updates the value_of_image field of the survey questions that have an image defined."""
    questions = env['of.survey.question.answer'].search(
        [('value_image', '!=', False), ('value_of_image_id', '=', False)]
    )
    for question in questions:
        question.value_image = question.value_image


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    _update_survey_images(cr, env)
