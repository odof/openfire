# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models
from odoo.tools import float_is_zero, float_compare, DEFAULT_SERVER_DATETIME_FORMAT

import odoo.addons.decimal_precision as dp


class OFSaleOrderLayoutCategory(models.Model):
    _inherit = 'of.sale.order.layout.category'

    price_subcontracted_service = fields.Float(
        string=u"PV HT sous-traité", digits=dp.get_precision('Product Price'),
        compute='_compute_price_subcontracted_service')
    cost_subcontracted_service = fields.Float(
        string=u"Coût sous-traitance", digits=dp.get_precision('Product Price'),
        compute='_compute_price_subcontracted_service')

    @api.depends('order_line_ids')
    def _compute_price_subcontracted_service(self):
        for category in self:
            subcontracted_service_lines = category.order_line_ids.filtered(lambda l: l.of_subcontracted_service)
            category.price_subcontracted_service = sum(subcontracted_service_lines.mapped('price_subtotal'))
            category.cost_subcontracted_service = sum(subcontracted_service_lines.mapped(
                lambda l: l.product_uom_qty * l.purchase_price))
