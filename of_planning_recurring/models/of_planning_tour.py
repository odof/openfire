# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, models


class OfPlanningTour(models.Model):
    _inherit = 'of.planning.tournee'

    @api.multi
    def _get_linked_interventions(self):
        """ Get the interventions linked to the tour, sorted by date.
        Add a domain leaf to remove recurring interventions that we don't want to manage in the tour.
        Recurring interventions aren't a planning tool for technicians, but a tool for the salesman team.
        """
        self.ensure_one()
        return self.env['of.planning.intervention'].search([
            ('employee_ids', 'in', self.employee_id.id),
            ('date', '<=', self.date),
            ('date_deadline', '>=', self.date),
            ('recurrency', '=', False),
            ('state', 'in', ('draft', 'confirm'))], order='date')
