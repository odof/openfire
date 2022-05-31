# -*- coding: utf-8 -*-


from odoo import api, fields, models
from odoo.tools import float_is_zero, float_compare, DEFAULT_SERVER_DATETIME_FORMAT

import odoo.addons.decimal_precision as dp


class OFSaleOrderLayoutCategory(models.Model):
    _inherit = 'of.sale.order.layout.category'

    price_subcontracted_service = fields.Float(
        string=u"PV HT sous-traité", digits=dp.get_precision('Product Price'),
        compute='_compute_price_subcontracted_service')

    @api.depends('order_line_ids')
    def _compute_price_subcontracted_service(self):
        for category in self:
            category.price_subcontracted_service = sum(category.order_line_ids.filtered(
                lambda l: l.of_property_subcontracted_service).mapped(
                lambda l: l.product_uom_qty * l.price_subtotal))
