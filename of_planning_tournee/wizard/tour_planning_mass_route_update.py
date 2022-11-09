# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import api, models


class OFTourPlanningMassRouteUpdateWizard(models.TransientModel):
    _name = 'of.tour.planning.mass.route.update.wizard'
    _description = "Tours Mass Route Update Wizard"

    @api.multi
    def action_button_validate(self):
        """ Updates route for the selected tours.
        """
        self.ensure_one()
        tours = self.env['of.planning.tournee'].sudo().browse(self._context.get('active_ids', []))
        tours and tours.action_compute_osrm_data(reload=True)
        tours and tours._compute_map_tour_line_ids()
