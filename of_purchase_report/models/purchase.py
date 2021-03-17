# -*- coding: utf-8 -*-

from odoo import models, api


class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    def write(self, vals):
        if 'invoice_lines' in vals:
            inv_lines = vals.pop('invoice_lines')
            line_ids = []
            for v in inv_lines:
                if v[0] == 2:
                    line_ids.append(v[1])
            self.env['account.invoice.line'].browse(line_ids).write({'purchase_line_id': False})
        return super(PurchaseOrderLine, self).write(vals)
