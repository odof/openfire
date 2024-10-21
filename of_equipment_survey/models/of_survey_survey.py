# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class OFSurveySurvey(models.Model):
    _inherit = "of.survey.survey"

    survey_type = fields.Selection(
        selection_add=[("equipment_survey", "Equipment Survey")],
        ondelete={"equipment_survey": "set default"},
    )
