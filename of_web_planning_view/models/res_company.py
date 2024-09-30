# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    of_planning_start_hour = fields.Integer(string="Day start time")
    of_planning_end_hour = fields.Integer(string="Day end time")

    def get_start_hour(self):
        return self.of_planning_start_hour

    def get_end_hour(self):
        return self.of_planning_end_hour
