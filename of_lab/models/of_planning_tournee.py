# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models, api


class OFPlanningTournee(models.Model):
    _inherit = 'of.planning.tournee'

    @api.model
    def of_planning_optimize_tour_demo(self, tour_id=1):
        tour = self.browse(tour_id)
        return tour.action_optimize_tour()
