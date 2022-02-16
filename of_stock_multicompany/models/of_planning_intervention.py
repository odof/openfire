# -*- coding: utf-8 -*-

from odoo import models, api


class OfPlanningIntervention(models.Model):
    _inherit = 'of.planning.intervention'

    @api.onchange('company_id')
    def onchange_company_id(self):
        super(OfPlanningIntervention, self).onchange_company_id()
        if self.company_id:
            self.warehouse_id = self.company_id.of_default_warehouse_id
