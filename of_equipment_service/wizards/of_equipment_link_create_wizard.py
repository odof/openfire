# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).


from odoo import Command, api, fields, models


class OFEquipmentLinkCreateWizard(models.TransientModel):
    _inherit = "of.equipment.link.create.wizard"

    def default_get(self, fields_list):
        default_values = super().default_get(fields_list)
        active_model = self.env.context.get("active_model")
        active_id = self.env.context.get("active_id")

        if active_model and active_id and active_model == "of.service.request":
            default_values["service_request_id"] = active_id
        return default_values

    service_request_id = fields.Many2one(comodel_name="of.service.request", string="Service Request")

    # -------------------------------------------------------------------------
    # Compute methods
    # -------------------------------------------------------------------------

    @api.depends("event_id", "service_request_id")
    def _compute_partner_id(self):
        super()._compute_partner_id()
        for wizard in self.filtered(lambda w: w.service_request_id and not w.partner_id):
            wizard.partner_id = wizard.service_request_id.partner_id or False

    @api.depends("event_id", "service_request_id")
    def _compute_address_id(self):
        super()._compute_address_id()
        for wizard in self.filtered(lambda w: w.service_request_id and not w.address_id):
            wizard.address_id = wizard.service_request_id.address_id or False

    # -------------------------------------------------------------------------
    # Action methods
    # -------------------------------------------------------------------------

    def action_button_select_equipments(self):
        action = super().action_button_select_equipments()
        if self.event_id:
            self.event_id.of_request_id._populate_service_request_equipment_line()
        if self.service_request_id:
            self.service_request_id._populate_service_request_equipment_line()
        return action

    # -------------------------------------------------------------------------
    # Business methods
    # -------------------------------------------------------------------------

    def _filter_records(self):
        """Overridden to filter the wizards based on the service request or the calendar event."""
        return self.filtered(lambda w: (w.service_request_id or w.event_id) and w.equipment_ids)

    def _create_equipment_links(self, vals_list):
        result = super()._create_equipment_links(vals_list)
        if self.service_request_id:
            self.service_request_id.write({"linked_equipment_ids": [Command.create(vals) for vals in vals_list]})
        return result

    def _get_line_values(self, equipment):
        values = super()._get_line_values(equipment)
        if self.service_request_id:
            return self.service_request_id._prepare_service_request_equipment_link_values_from_equipment(
                equipment=equipment
            )
        return values
