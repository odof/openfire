# -*- coding: utf-8 -*-

from odoo import models, fields, api


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    @api.multi
    def _cart_find_product_line(self, product_id=None, line_id=None, **kwargs):
        self.ensure_one()
        lines = super(SaleOrder, self)._cart_find_product_line(product_id, line_id)
        if line_id:
            return lines
        domain = [('id', 'in', lines.ids), ('of_fuel_choice', '=', False)]
        return self.env['sale.order.line'].sudo().search(domain)


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    of_fuel_choice = fields.Boolean(string=u"Ligne issue du choix de combustible web")
