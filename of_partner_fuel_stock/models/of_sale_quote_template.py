# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models, fields, api


class SaleQuoteLine(models.Model):
    _inherit = 'sale.quote.line'

    of_storage = fields.Boolean(string='Storage and withdrawal on demand of articles')

    @api.onchange('product_id')
    def _onchange_product_id(self):
        res = super(SaleQuoteLine, self)._onchange_product_id()
        new_vals = {'of_storage': self.product_id.of_storage}
        self.update(new_vals)
        return res

    @api.onchange('of_storage')
    def onchange_of_storage(self):
        if self.of_is_kit:
            self.kit_id.kit_line_ids.write({'of_storage': self.of_storage, 'of_storage_readonly': not self.of_storage})

    @api.onchange('no_update')
    def _onchange_no_update(self):
        res = super(SaleQuoteLine, self)._onchange_no_update()
        if self.no_update and self.product_id.of_is_kit:
            self.kit_id.kit_line_ids.write({'of_storage': self.of_storage, 'of_storage_readonly': not self.of_storage})
        return res

    def get_saleorder_kit_data(self):
        res = super(SaleQuoteLine, self).get_saleorder_kit_data()
        if not self.of_is_kit:
            return {}
        if self.no_update:
            for kit_line in res['kit_line_ids']:
                if len(kit_line) >= 3 and kit_line[2] and kit_line[2]['product_id']:
                    quote_kit_line = self.kit_id.kit_line_ids.filtered(
                        lambda l: l.product_id.id == kit_line[2]['product_id'])
                    if len(quote_kit_line) > 1:
                        quote_kit_line = quote_kit_line.filtered(
                            lambda l: l.sequence == kit_line[2]['sequence'] and
                            l.qty_per_kit == kit_line[2]['qty_per_kit'] and
                            l.price_unit == kit_line[2]['price_unit'])
                    if len(quote_kit_line) > 1:
                        quote_kit_line = quote_kit_line[0]
                    kit_line[2]['of_storage'] = quote_kit_line.of_storage
                    kit_line[2]['of_storage_readonly'] = quote_kit_line.of_storage_readonly
        else:
            if self.of_storage:
                for kit_line in res['kit_line_ids']:
                    if len(kit_line) >= 3 and kit_line[2] and kit_line[2]['product_id']:
                        product_id = self.env['product.product'].browse(kit_line[2]['product_id'])
                        kit_line[2]['of_storage'] = product_id.of_storage
            else:
                for kit_line in res['kit_line_ids']:
                    if len(kit_line) >= 3 and kit_line[2] and kit_line[2]['product_id']:
                        kit_line[2]['of_storage_readonly'] = True
        return res
