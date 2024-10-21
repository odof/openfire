# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import _, api, fields, models
from odoo.exceptions import UserError


class OFServiceRequestEquipmentLink(models.Model):
    """
    Link between a service request and an equipment.

    When planning an intervention from a service request an equipment a link (`of.calendar.event.equipment.link`) is
    created between the event and the equipment for each equipment in the service request. And service request id is
    stored in the calendar event link.

    Then when modifying the equipment/task/report on an equipment link in the event, the link is updated in the service
    request and vice versa. All its done through `of.service.request.write()` and `of.calendar.event.write()`.

    This object is not intended to be used directly by `of.service.request.equipment.link.write()` call, but through
    the service request form/write to ensure data synchronization between the service request and event.

    If you directly call the create/write/unlink methods of this object, you will have to ensure the synchronization
    yourself.
    """

    _name = "of.service.request.equipment.link"
    _description = "Service Request Equipment Link"
    _inherit = "of.planning.equipment.link.mixin"

    service_request_id = fields.Many2one(
        comodel_name="of.service.request", string="Service request", required=True, ondelete="cascade"
    )
    partner_id = fields.Many2one(related="service_request_id.partner_id")
    address_id = fields.Many2one(related="service_request_id.address_id")

    # -------------------------------------------------------------------------
    # ORM methods
    # -------------------------------------------------------------------------

    @api.model_create_multi
    def create(self, vals_list):
        self._add_missing_service_request_equipment_link_fields(vals_list)
        if (
            (
                service_requests := self.env["of.service.request"].browse(
                    [vals["service_request_id"] for vals in vals_list]
                )
            )
            and any(service_request.state in ("done", "cancel") for service_request in service_requests)
            and not self.env.context.get("of_ignore_request_state")
        ):
            raise UserError(_("You cannot create equipment links for done or cancelled service requests."))
        return super().create(vals_list)

    def unlink(self):
        if any(link.service_request_id.state in ("done", "cancel") for link in self) and not self.env.context.get(
            "of_ignore_request_state"
        ):
            raise UserError(_("You cannot delete equipment links for done or cancelled service requests."))
        return super().unlink()

    def write(self, vals):
        if any(link.service_request_id.state in ("done", "cancel") for link in self) and not self.env.context.get(
            "of_ignore_request_state"
        ):
            raise UserError(_("You cannot change equipment links for done or cancelled service requests."))
        return super().write(vals)

    # -------------------------------------------------------------------------
    # Business methods
    # -------------------------------------------------------------------------

    def _add_missing_service_request_equipment_link_fields(self, vals_list):
        """Add required missing fields like report template and task to the equipment link values if they are not
        present."""
        self._add_missing_mixin_link_fields(
            inverse_field_key="service_request_id", template_field="template_id", vals_list=vals_list
        )

    def _post_self_update_message(self, old_values=None, new_values=None):
        """Post a message to the service request's chatter when equipment details are updated from itself."""
        self.ensure_one()
        if not old_values or not new_values:
            return

        changes = self._get_changes_message_post(old_values, new_values)
        old_equipment = self.env["of.equipment"].browse(old_values.get("equipment_id"))
        self.service_request_id.message_post(
            body=_(
                "Equipment details have been updated for %(equipment)s.<br/>%(changes)s",
                equipment=old_equipment.name,
                changes=changes,
            )
        )
        return True

    def _post_request_message(self, event=None, old_values=None, new_values=None):
        """Post a message to the service request's chatter when equipment details are updated from the event."""
        self.ensure_one()
        if not event or not old_values or not new_values:
            return

        changes = self._get_changes_message_post(old_values, new_values)
        old_equipment = self.env["of.equipment"].browse(old_values.get("equipment_id"))
        self.service_request_id.message_post(
            body=_(
                "Equipment details have been updated on the event (%(event)s) for %(equipment)s.<br/>%(changes)s",
                event=event._get_html_link(),
                equipment=old_equipment.name,
                changes=changes,
            )
        )
        return True
