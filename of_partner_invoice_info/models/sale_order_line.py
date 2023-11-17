# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models, fields, api, _


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    of_price_pending = fields.Float(string=u"Montant encours", compute='_compute_of_price_pending')

    def _compute_of_price_pending(self):
        for line in self:
            line.of_price_pending = \
                    line.price_total * (line.product_uom_qty - line.qty_invoiced) / line.product_uom_qty \
                    if line.product_uom_qty else 0.0
