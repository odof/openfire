# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import Command, _, api, fields, models
from odoo.exceptions import UserError


class OFCalendarEventEquipmentLink(models.Model):
    _name = "of.calendar.event.equipment.link"
    _description = "Calendar Event Equipment Link"
    _inherit = "of.planning.equipment.link.mixin"

    event_id = fields.Many2one(comodel_name="calendar.event", string="Event", required=True, ondelete="cascade")
    partner_id = fields.Many2one(comodel_name="res.partner", related="event_id.of_partner_id", string="Customer")
    address_id = fields.Many2one(comodel_name="res.partner", related="event_id.of_address_id", string="Address")
    equipment_id = fields.Many2one(
        domain="["
        "('customer_id', '=', partner_id), '|', ('site_address_id', '=', address_id), "
        "('customer_id', '=', address_id)"
        "]",
    )
    fiscal_position_id = fields.Many2one(
        related="event_id.of_fiscal_position_id", string="Fiscal Position", readonly=False
    )
    brand_id = fields.Many2one(related="equipment_id.brand_id", string="Brand")
    product_id = fields.Many2one(related="equipment_id.product_id", string="Product")
    model_name = fields.Char(related="equipment_id.model_name", string="Model")
    note = fields.Text(related="equipment_id.note", string="Note")
    site_address_id = fields.Many2one(related="equipment_id.site_address_id", string="Site Address")
    site_street = fields.Char(related="site_address_id.street", string="Street")
    site_street2 = fields.Char(related="site_address_id.street2", string="Street2")
    site_zip = fields.Char(related="site_address_id.zip", string="Zip")
    site_city = fields.Char(related="site_address_id.city", string="City")
    site_country_id = fields.Many2one(related="site_address_id.country_id", string="Country")
    report_text = fields.Text(string="Report")
    line_ids = fields.One2many(
        comodel_name="of.calendar.event.equipment.link.line", inverse_name="link_id", string="Invoicing lines"
    )
    all_image_ids = fields.One2many(comodel_name="of.image", inverse_name="equipment_link_id", string="Images")

    # -------------------------------------------------------------------------
    # ORM methods
    # -------------------------------------------------------------------------

    @api.model_create_multi
    def create(self, vals_list):
        self._add_missing_calendar_equipment_link_fields(vals_list)
        if (
            (events := self.env["calendar.event"].browse([vals["event_id"] for vals in vals_list]))
            and any(event.of_state in ("done", "cancel") for event in events)
            and not self.env.context.get("of_ignore_event_state")
        ):
            raise UserError(_("You cannot create equipment links for done or cancelled events."))
        return super().create(vals_list)

    def unlink(self):
        if any(link.event_id.of_state in ("done", "cancel") for link in self) and not self.env.context.get(
            "of_ignore_event_state"
        ):
            raise UserError(_("You cannot delete equipment links for done or cancelled events."))
        return super().unlink()

    def write(self, vals):
        if any(link.event_id.of_state in ("done", "cancel") for link in self) and not self.env.context.get(
            "of_ignore_event_state"
        ):
            raise UserError(_("You cannot change equipment links for done or cancelled events."))
        return super().write(vals)

    # -------------------------------------------------------------------------
    # Action methods
    # -------------------------------------------------------------------------

    def action_button_open_equipment_link(self):
        self.ensure_one()
        return {
            "name": _("Equipment"),
            "type": "ir.actions.act_window",
            "res_model": "of.calendar.event.equipment.link",
            "view_mode": "form",
            "res_id": self.id,
            "context": {"default_event_id": self.event_id.id},
            "target": "current",
        }

    def action_button_back_to_event(self):
        self.ensure_one()
        action_url = (
            f"/web#id={self.event_id.id}&model={self.event_id._name}&view_type=form&"
            f'action={self.env.ref("of_planning.action_calendar_event").id}&'
            f'menu_id={self.env.ref("of_planning.menu_of_planning_main").id}'
        )
        return {
            "type": "ir.actions.act_url",
            "name": _("Back to Event"),
            "target": "self",
            "url": action_url,
        }

    # -------------------------------------------------------------------------
    # Business methods
    # -------------------------------------------------------------------------

    def _add_missing_calendar_equipment_link_fields(self, vals_list):
        """Add report template and task to the equipment link values if not present."""
        self._add_missing_mixin_link_fields(
            inverse_field_key="event_id", template_field="of_template_id", vals_list=vals_list
        )
        # Add calendar event equipment link invoicing lines
        for vals in vals_list:
            if not vals.get("line_ids") and vals.get("equipment_report_tmpl_id"):
                template = self.env["of.equipment.intervention.report.template"].browse(
                    vals["equipment_report_tmpl_id"]
                )
                if template.line_ids:
                    vals["line_ids"] = [
                        Command.create(
                            {"product_id": line.product_id.id, "qty": line.qty, "price_unit": line.price_unit}
                        )
                        for line in template.line_ids
                    ]
