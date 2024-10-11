# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class ResPartner(models.Model):
    _name = "res.partner"
    _inherit = ["res.partner", "utm.mixin"]

    user_id = fields.Many2one(default=lambda self: self.env.user)
    of_canvasser_id = fields.Many2one(comodel_name="res.users", string="Canvasser")
    of_lead_campaign_id = fields.Many2one(
        comodel_name="utm.campaign", compute="_compute_of_lead_utm", string="Campaign (lead)"
    )
    of_lead_medium_id = fields.Many2one(
        comodel_name="utm.medium", string="Channel (lead)", compute="_compute_of_lead_utm"
    )
    of_lead_source_id = fields.Many2one(comodel_name="utm.source", string="Source", compute="_compute_of_lead_utm")

    @api.depends("opportunity_ids")
    def _compute_of_lead_utm(self):
        for partner in self:
            if partner.opportunity_ids:
                partner.of_lead_campaign_id = partner.opportunity_ids[0].campaign_id.id
                partner.of_lead_source_id = partner.opportunity_ids[0].source_id.id
                partner.of_lead_medium_id = partner.opportunity_ids[0].medium_id.id
            else:
                partner.of_lead_campaign_id = False
                partner.of_lead_source_id = False
                partner.of_lead_medium_id = False
