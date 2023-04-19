# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models, api


class StockLocation(models.Model):
    _inherit = 'stock.location'

    @api.model
    def _init_res_loc(self):
        res_loc = self.env.ref('stock_reserve.stock_location_reservation')
        res_loc.company_id = False
        return True
