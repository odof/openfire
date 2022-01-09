# -*- coding: utf-8 -*-

from odoo import api, fields, models
from odoo.exceptions import ValidationError
import odoo.addons.decimal_precision as dp

import math


class StockWarehouseOrderpoint(models.Model):
    _inherit = 'stock.warehouse.orderpoint'

    def _default_of_delivery_delay(self):
        of_delivery_delay = 0
        if self.product_id and self.product_id.seller_ids:
            of_delivery_delay = self.product_id.seller_ids[0].delay
        return of_delivery_delay

    of_forecast_qty = fields.Float(string=u"Qté Prév. N", digits=dp.get_precision('Product Unit of Measure'))
    of_pace_of_sale = fields.Float(string=u"Rythme de vente", digits=(16, 2), compute='_compute_of_pace_of_sale')
    of_delivery_delay = fields.Integer(string=u"Délai de livraison", default=_default_of_delivery_delay)
    of_min_theoretical_qty = fields.Float(
        string=u"Qté mini théorique", digits=(16, 2), compute='_compute_of_min_theoretical_qty')
    of_min_stock_coef = fields.Float(string=u"Coef stock min", digits=(16, 2), default=1.0)
    of_max_stock_coef = fields.Float(string=u"Coef stock maxi", digits=(16, 2), default=1.0)

    @api.depends('of_forecast_qty')
    def _compute_of_pace_of_sale(self):
        if self.of_forecast_qty:
            self.of_pace_of_sale = 1 / (self.of_forecast_qty / 365)

    @api.depends('of_delivery_delay', 'of_pace_of_sale')
    def _compute_of_min_theoretical_qty(self):
        if self.of_pace_of_sale:
            self.of_min_theoretical_qty = self.of_delivery_delay / self.of_pace_of_sale

    @api.multi
    def compute_min_max_qty(self):
        """Calcul des quantités mini et maxi des règles de stocks"""

        for orderpoint in self:
            # On ne valorise qty min/max que si la qté min théorique est remplie
            if orderpoint.of_min_theoretical_qty:
                product_min_qty = orderpoint.of_min_theoretical_qty * orderpoint.of_min_stock_coef
                self.product_min_qty = math.ceil(product_min_qty)
                self.product_max_qty = max(math.floor(product_min_qty * orderpoint.of_max_stock_coef),
                                           self.product_min_qty)

    @api.constrains('of_min_stock_coef', 'of_max_stock_coef')
    def constraint_stock_coef(self):
        if not self.of_max_stock_coef or not self.of_min_stock_coef:
            raise ValidationError(u"Un coefficient doit toujours être supérieur à 0")
        if self.of_max_stock_coef < 1.0:
            raise ValidationError(u"Le coef de stock maxi doit toujours être supérieur ou égal a 1")

    @api.onchange('product_id')
    def onchange_product_id(self):
        of_delivery_delay = 0
        if self.product_id and self.product_id.seller_ids:
            of_delivery_delay = self.product_id.seller_ids[0].delay
        self.of_delivery_delay = of_delivery_delay
