# -*- coding: utf-8 -*-

from odoo import api, models


class StockProductionLot(models.Model):
    _inherit = 'stock.production.lot'

    @api.multi
    def _get_new_parc_values(self, picking):
        values = super(StockProductionLot, self)._get_new_parc_values(picking)
        values.update({'company_id': picking.company_id.id})
        return values
