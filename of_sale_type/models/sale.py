# -*- coding: utf-8 -*-

from odoo import api, fields, models


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    of_sale_type_id = fields.Many2one(comodel_name='of.sale.type', string="Sale order type")

    @api.onchange('of_template_id')
    def onchange_template_id(self):
        # Change the order type if the selected quote template has one
        super(SaleOrder, self).onchange_template_id()
        if self.of_template_id and self.of_template_id.of_sale_type_id:
            self.of_sale_type_id = self.of_template_id.of_sale_type_id

    @api.multi
    def _prepare_invoice(self):
        # self.ensure_one() already done in the super
        vals = super(SaleOrder, self)._prepare_invoice()
        if vals and isinstance(vals, dict) and self.of_sale_type_id:
            vals['of_sale_type_id'] = self.of_sale_type_id.id
        return vals


class SaleQuoteTemplate(models.Model):
    _inherit = "sale.quote.template"

    of_sale_type_id = fields.Many2one(comodel_name='of.sale.type', string="Sale order type")


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    of_sale_type_id = fields.Many2one(related='order_id.of_sale_type_id', string="Sale order type", readonly=True,
                                      store=True)
