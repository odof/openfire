# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import api, models, fields, _


class OFPlanningTournee(models.Model):
    _inherit = 'of.planning.tournee'

    website_intervention = fields.Boolean(
        string="Intervention created from website", compute='_compute_website_intervention',
        help="If there is at least one intervention created from the website on Tour, this field is True")

    @api.multi
    def _compute_website_intervention(self):
        for tour in self:
            tour.website_intervention = any(tour.tour_line_ids.mapped('created_from_website'))


class OFPlanningTourneeLine(models.Model):
    _inherit = 'of.planning.tour.line'

    created_from_website = fields.Boolean(
        string="Created from website", related='intervention_id.website_create', readonly=True)
