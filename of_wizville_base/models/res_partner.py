# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class ResPartner(models.Model):
    _inherit = "res.partner"

    of_wizville_satisfaction = fields.Char(string="Global satisfaction")
    of_nps_pose_score = fields.Char(string="NPS Score")
    of_nps_date_submission = fields.Char(string="Date of NPS submission")
    of_nps_date_response = fields.Char(string="NPS response date")
