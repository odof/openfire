# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models
from odoo.tools.safe_eval import safe_eval


class ResPartner(models.Model):
    _inherit = "res.partner"

    of_com_sector_id = fields.Many2one(  # Changed into computed M2O field (onchange)
        compute="_compute_of_com_sector_id",
        store=True,
        readonly=False,
    )
    of_intervention_partner_ids = fields.One2many(
        comodel_name="calendar.event", string="Customer's Interventions", inverse_name="of_partner_id"
    )
    of_intervention_address_ids = fields.One2many(
        comodel_name="calendar.event", string="Address's Interventions", inverse_name="of_address_id"
    )
    of_intervention_ids = fields.Many2many(
        comodel_name="calendar.event", string="Interventions", compute="_compute_of_interventions_data"
    )
    of_intervention_count = fields.Integer(string="# Interventions", compute="_compute_of_interventions_data")
    of_is_intervention_warn = fields.Boolean(string="Interventions Warning")

    # --------------------------------------------------------------------------
    # Compute methods
    # --------------------------------------------------------------------------

    @api.depends("of_com_sector_id", "zip")
    def _compute_of_tech_sector_id(self):
        for partner in self:
            automatic_sectors = self.env.user.company_id.of_automatic_sectors
            if partner.zip and automatic_sectors:
                partner.of_tech_sector_id = self.env["of.sector"].get_sector_from_zip_code(
                    partner.zip, ("technical", "technical_commercial")
                )
        return super()._compute_of_tech_sector_id()

    @api.depends("zip")
    def _compute_of_com_sector_id(self):
        for partner in self:
            automatic_sectors = self.env.user.company_id.of_automatic_sectors
            if partner.zip and automatic_sectors:
                partner.of_com_sector_id = self.env["of.sector"].get_sector_from_zip_code(
                    partner.zip, ("commercial", "technical_commercial")
                )

    def _compute_of_interventions_data(self):
        calendar_event_obj = self.sudo().env["calendar.event"]
        for partner in self:
            intervention_ids = calendar_event_obj.search(
                [
                    "|",
                    ("of_partner_id", "child_of", partner.id),
                    ("of_address_id", "child_of", partner.id),
                ]
            )
            partner.of_intervention_ids = intervention_ids
            partner.of_intervention_count = len(intervention_ids)

    @api.depends("of_is_intervention_warn")
    def _compute_of_is_warn(self):
        has_warn = self.filtered("of_is_intervention_warn")
        for partner in has_warn:
            partner.of_is_warn = True
        partners_left = self - has_warn
        super(ResPartner, partners_left)._compute_of_is_warn()

    # ----------------------------------------------------------------------------
    # Actions methods
    # ----------------------------------------------------------------------------

    def action_button_view_intervention(self):
        events = self.mapped("of_intervention_ids")
        action = self.env.ref("of_planning.action_calendar_event").sudo().read()[0]
        action["domain"] = [("of_partner_id", "child_of", self.ids), ("of_address_id", "child_of", self.ids)]
        if len(self.ids) == 1:
            action["context"] = self._get_action_view_intervention_context(safe_eval(action["context"]))
            if len(events) == 1:
                action["res_id"] = events[0].id
        action = events._get_calendar_event_action_views(action)
        return action

    # ----------------------------------------------------------------------------
    # Business methods
    # ----------------------------------------------------------------------------

    def _get_action_view_intervention_context(self, context=None):
        if context is None:
            context = {}
        context.update(
            {
                "default_of_partner_id": self.id,
                "default_of_address_id": self.id,
                "default_start_date": fields.Date.today(),
            }
        )
        return context
