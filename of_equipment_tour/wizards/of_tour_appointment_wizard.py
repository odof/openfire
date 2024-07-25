# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models


class OFTourAppointmentWizard(models.TransientModel):
    _inherit = 'of.tour.appointment.wizard'

    def _prepare_calendar_event_values(self):
        vals = super()._prepare_calendar_event_values()
        vals.update({'of_use_equipment': self.request_id and self.request_id.use_equipment})
        return vals
