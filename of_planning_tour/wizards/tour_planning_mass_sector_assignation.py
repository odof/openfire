# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import Command, fields, models


class OFPlanningTourMassSectorAssignationWizard(models.TransientModel):
    """Tours Mass Sector Assignation Wizard"""

    _name = "of.planning.tour.mass.sector.assignation.wizard"
    _description = __doc__

    sector_id = fields.Many2one(comodel_name="of.sector", string="Sector to assign")

    def action_button_validate(self):
        """Assign a new sector to the tours.
        If a tour has already an intervention with a different sector, tour will not be assigned to the new sector
        """
        self.ensure_one()

        tours = self.env["of.planning.tour"].browse(self._context.get("active_ids", []))
        tours_wo_lines = tours.filtered(lambda t: not t.tour_line_ids)
        tours_w_lines = tours.filtered(lambda t: t.tour_line_ids)
        for tour in tours_w_lines:
            dodge_tour = any(
                line.intervention_id.of_sector_id.id != self.sector_id.id
                for line in tour.tour_line_ids.filtered(
                    lambda line: line.intervention_id and line.intervention_id.of_sector_id
                )
            )
            if dodge_tour:
                tours_w_lines -= tour

        tours_to_update = tours_wo_lines + tours_w_lines
        tours_to_update.write({"sector_ids": [Command.link(self.sector_id.id)]})
