# -*- coding: utf-8 -*-

from odoo import api, models

class OfPlanningIntervention(models.Model):
    _inherit = "of.planning.intervention"

    @api.multi
    def _get_invoicing_company(self, partner):
        return partner.company_id
