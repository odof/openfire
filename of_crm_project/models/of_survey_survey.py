# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class OFSurveySurvey(models.Model):
    _inherit = 'of.survey.survey'

    show_start = fields.Boolean(string="Show start page")
    show_end = fields.Boolean(string="Show end page")
