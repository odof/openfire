# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import _, fields, models


class OFCalendarEventEquipmentLink(models.Model):
    """
    Link between a calendar event and an equipment.

    To ensure data synchronization between the service request links and the event links we store service request id in
    link in the event link. This way we can update the request link when the event link is modified and vice versa.

    This object is not intended to be used directly by `of.calendar.event.equipment.link.write()` call, but through the
    event form/write to ensure data synchronization between the service request and event.

    If you directly call the create/write/unlink methods of this object, you will have to ensure the synchronization
    yourself.
    """

    _inherit = "of.calendar.event.equipment.link"

    request_link_id = fields.Many2one(
        comodel_name="of.service.request.equipment.link",
        string="Request Link",
        help="Technical field to store link that created this line.",
    )

    def _prepare_service_request_equipment_link_values(self):
        return {
            "equipment_id": self.equipment_id.id,
            "task_id": self.task_id.id,
            "equipment_report_tmpl_id": self.equipment_report_tmpl_id.id,
        }

    def _post_event_message(self, old_values=None, new_values=None):
        """Post a message to the event's chatter when equipment details are updated."""
        self.ensure_one()
        if not old_values or not new_values:
            return

        changes = self._get_changes_message_post(old_values, new_values)
        old_equipment = self.env["of.equipment"].browse(old_values.get("equipment_id"))
        self.event_id.message_post(
            body=_(
                "Equipment details have been updated on the service request for %(equipment)s.<br/>%(changes)s",
                equipment=old_equipment.name,
                changes=changes,
            )
        )
        return True
