# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import Command, models


class OFTourAppointmentWizard(models.TransientModel):
    _inherit = "of.tour.appointment.wizard"

    def _prepare_calendar_event_values(self):
        values = super()._prepare_calendar_event_values()

        # Copy linked equipment and its lines and images, etc. to the new intervention
        equipment_links = []
        for eq_link in self.intervention_id.of_linked_equipment_ids:
            new_eq_link_values = eq_link.copy_data()[0]
            line_ids = []
            for line in eq_link.line_ids:
                new_line_values = line.copy_data()[0]
                new_line_values["link_id"] = False
                line_ids.append(Command.create(new_line_values))
            all_image_ids = []
            for image in eq_link.all_image_ids:
                new_image_values = image.copy_data()[0]
                new_image_values["equipment_link_id"] = False
                all_image_ids.append(Command.create(new_image_values))
            new_eq_link_values["line_ids"] = line_ids
            new_eq_link_values["all_image_ids"] = all_image_ids
            equipment_links.append(Command.create(new_eq_link_values))
        values.update(
            {
                "of_use_equipment": self.request_id and self.request_id.use_equipment,
                "of_linked_equipment_ids": equipment_links,
            }
        )
        return values
