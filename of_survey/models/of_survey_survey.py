# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class OFSurveySurvey(models.Model):
    _name = 'of.survey.survey'
    _inherit = 'survey.survey'

    survey_type = fields.Selection(
        required=True,
        default='lead_opportunity',
        selection=[('lead_opportunity', "Lead/Opportunity"), ('intervention_survey', "Intervention Survey")],
    )
