# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class OFSurveySurvey(models.Model):
    _inherit = 'of.survey.survey'

    survey_type = fields.Selection(
        selection_add=[('intervention_survey', "Intervention Survey")],
        ondelete={'intervention_survey': 'set default'},
    )
    show_start = fields.Boolean(string="Show start page")
    show_end = fields.Boolean(string="Show end page")
