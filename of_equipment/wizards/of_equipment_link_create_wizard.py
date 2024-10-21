# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).


from odoo import Command, api, fields, models


class OFEquipmentLinkCreateWizard(models.TransientModel):
    _name = "of.equipment.link.create.wizard"
    _description = "Equipment Link Create Wizard"

    def default_get(self, fields_list):
        default_values = super().default_get(fields_list)
        active_model = self.env.context.get("active_model")
        active_id = self.env.context.get("active_id")

        if active_model and active_id and active_model == "calendar.event":
            default_values["event_id"] = active_id
        return default_values

    event_id = fields.Many2one(comodel_name="calendar.event", string="Event")
    partner_id = fields.Many2one(comodel_name="res.partner", compute="_compute_partner_id", store=True)
    address_id = fields.Many2one(comodel_name="res.partner", compute="_compute_address_id", store=True)
    equipment_ids = fields.Many2many(
        comodel_name="of.equipment",
        domain="[('customer_id', '=', partner_id), '|', ('site_address_id', '=', address_id), "
        "('customer_id', '=', address_id)]",
    )

    # -------------------------------------------------------------------------
    # Compute methods
    # -------------------------------------------------------------------------

    @api.depends("event_id")
    def _compute_partner_id(self):
        for wizard in self:
            wizard.partner_id = wizard.event_id.of_partner_id

    @api.depends("event_id")
    def _compute_address_id(self):
        for wizard in self:
            wizard.address_id = wizard.event_id.of_address_id

    # -------------------------------------------------------------------------
    # Action methods
    # -------------------------------------------------------------------------

    def action_select_equipments(self):
        """Action method to create the equipment links on the the calendar event."""
        vals_list = []
        for wizard in self._filter_records():
            for equipment in wizard.equipment_ids:
                if vals := wizard._get_line_values(equipment):
                    vals_list.append(vals)
        if vals_list:
            self._create_equipment_links(vals_list)
        return {"type": "ir.actions.act_window_close"}

    def action_button_select_equipments(self):
        return self.action_select_equipments()

    # -------------------------------------------------------------------------
    # Business methods
    # -------------------------------------------------------------------------

    def _filter_records(self):
        """Filter the wizards based on the calendar event and the equipment."""
        return self.filtered(lambda w: w.event_id and w.equipment_ids)

    def _create_equipment_links(self, vals_list):
        """Create the equipment link on the calendar event."""
        if self.event_id:
            self.event_id.write({"of_linked_equipment_ids": [Command.create(vals) for vals in vals_list]})

    def _get_line_values(self, equipment):
        """Get the values for the equipment link line to create."""
        if self.event_id:
            return self.event_id._prepare_calendar_event_equipment_link_values_from_equipment(equipment=equipment)
        return {}
