# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class StockInventory(models.Model):
    _inherit = 'stock.inventory'

    location_id = fields.Many2one(default=lambda s:s._default_location_id())

    @api.model
    def _default_location_id(self):
        company_user = self.env.user.company_id
        warehouse = company_user.of_default_warehouse_id
        if warehouse:
            return warehouse.lot_stock_id.id
        else:
            return super(StockInventory, self)._default_location_id()
