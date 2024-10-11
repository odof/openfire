from odoo import Command, api, fields, models


class OFResPartnerAssignAreaWizard(models.TransientModel):
    "Wizard for assigning sectors to partners"

    _name = "of.res.partner.assign.sector.wizard"
    _description = __doc__

    @api.model
    def default_get(self, fields):
        result = super().default_get(fields)
        if self._context.get("active_model") == "res.partner" and self._context.get("active_ids"):
            result["partner_ids"] = [Command.set(self._context["active_ids"])]
        return result

    partner_ids = fields.Many2many(comodel_name="res.partner", string="Partners to update")
    sector_id = fields.Many2one(comodel_name="of.sector", string="Sector", required=True)
    sector_type = fields.Selection(
        selection=[
            ("technical", "Technical"),
            ("commercial", "Commercial"),
            ("technical_commercial", "Technical & Commercial"),
        ],
        string="Sector type",
        required=True,
    )

    def action_button_update(self):
        self.ensure_one()
        if self.sector_type == "technical":
            self.partner_ids.write({"of_tech_sector_id": self.sector_id.id})
        elif self.sector_type == "commercial":
            self.partner_ids.write({"of_com_sector_id": self.sector_id.id})
        elif self.sector_type == "technical_commercial":
            self.partner_ids.write({"of_tech_sector_id": self.sector_id.id, "of_com_sector_id": self.sector_id.id})
        return True
