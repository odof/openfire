# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class OFSurveyQuestion(models.Model):
    _inherit = "of.survey.question"

    constr_no_report_display = fields.Boolean(
        string="Do not display in reports",
        default=False,
        help="This question will not be displayed in the intervention report",
    )
