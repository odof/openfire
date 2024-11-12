# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import Command, models


class OFTourAppointmentWizard(models.TransientModel):
    _inherit = "of.tour.appointment.wizard"

    def _prepare_calendar_event_values(self):
        vals = super()._prepare_calendar_event_values()
        vals.update({"of_section_to_display_ids": [Command.set(self.template_id.section_to_display_ids.ids)]})
        return vals
