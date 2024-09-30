# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models


class Attendee(models.Model):
    _inherit = "calendar.attendee"

    def _should_notify_attendee(self):
        """Override to not notify attendees for interventions"""
        return super()._should_notify_attendee() and self.event_id.of_type != "intervention"
