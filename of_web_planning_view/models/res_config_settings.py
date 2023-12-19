# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    of_planning_start_hour = fields.Integer(
        string="Day start time", related="company_id.of_planning_start_hour", readonly=False
    )
    of_planning_end_hour = fields.Integer(
        string="Day end time", related="company_id.of_planning_end_hour", readonly=False
    )
