# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class OFPlanningInterventionTemplate(models.Model):
    _inherit = "of.planning.intervention.template"

    website_published = fields.Boolean(string="Published on website")
    website_name = fields.Char(string="Website label")
    is_fixed_meeting = fields.Boolean(string="Fixed meeting")
    fixed_address_id = fields.Many2one(comodel_name="res.partner", string="Fixed address")

    def action_button_toggle_web(self):
        self.ensure_one()
        self.website_published = not self.website_published
