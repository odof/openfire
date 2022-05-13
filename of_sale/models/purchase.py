# -*- coding: utf-8 -*-
from odoo import models, fields, api


class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    of_order_line_option_id = fields.Many2one(comodel_name='of.order.line.option', string=u"Option")

    @api.onchange('of_order_line_option_id')
    def _onchange_of_order_line_option_id(self):
        if self.of_order_line_option_id and self.product_id:
            option = self.of_order_line_option_id
            if option.purchase_price_update and self.price_unit:
                if option.purchase_price_update_type == 'fixed':
                    self.price_unit = self.price_unit + option.purchase_price_update_value
                elif option.purchase_price_update_type == 'percent':
                    self.price_unit = self.price_unit + (self.price_unit * (option.purchase_price_update_value / 100))
                self.price_unit = self.order_id.currency_id.round(self.price_unit)
            self.name = self.name + "\n%s" % option.description_update
