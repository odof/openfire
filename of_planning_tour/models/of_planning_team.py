# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class OFPlanningTeam(models.Model):
    _inherit = "of.planning.team"

    start_address_id = fields.Many2one(
        comodel_name="res.partner",
        string="Start Address",
        compute="_compute_start_address_id",
        store=True,
        readonly=False,
    )
    return_address_id = fields.Many2one(
        comodel_name="res.partner",
        string="Return Address",
        compute="_compute_return_address_id",
        store=True,
        readonly=False,
    )
    partner_latitude = fields.Float(related="start_address_id.partner_latitude")
    partner_longitude = fields.Float(related="start_address_id.partner_longitude")

    @api.depends("employee_ids")
    def _compute_start_address_id(self):
        for team in self:
            if team.employee_ids:
                team.start_address_id = team.employee_ids[0].address_home_id
            else:
                team.start_address_id = False

    @api.depends("employee_ids", "start_address_id")
    def _compute_return_address_id(self):
        cache = {}
        team_with_employee = self.filtered("employee_ids")
        for team in team_with_employee:
            key = (team.employee_ids[0].id or False, team.start_address_id.id, team.return_address_id.id)
            if key not in cache:
                cache[key] = team.employee_ids[0].address_home_id
            team.return_address_id = cache[key]
        for team in self - team_with_employee:
            team.return_address_id = False
