# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models


class OFTourPlanningMassRouteUpdateWizard(models.TransientModel):
    """Tours Mass Route Update Wizard."""

    _name = "of.planning.tour.mass.route.update.wizard"
    _description = __doc__

    def action_button_validate(self):
        """Updates route for the selected tours."""
        self.ensure_one()
        tours = self.env["of.planning.tour"].sudo().browse(self._context.get("active_ids", []))
        tours and tours.action_compute_osrm_data(reload=True)
        tours and tours._compute_map_tour_line_ids()
