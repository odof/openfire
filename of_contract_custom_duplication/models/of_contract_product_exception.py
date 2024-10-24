# -*- coding: utf-8 -*-

from odoo import api, models


class OFContractProductException(models.Model):
    _inherit = 'of.contract.product.exception'

    @api.multi
    def copy_contract_line_exception_vals(self):
        self.ensure_one()
        return {
            'date_invoice_next': self.date_invoice_next,
            'product_id': self.product_id.id,
            'name': self.name,
            'qty': self.qty,
            'qty_invoiced': self.qty_invoiced,
            'price_unit': self.price_unit,
            'purchase_price': self.purchase_price,
            'tax_ids': [(4, tax.id) for tax in self.tax_ids],
            'internal_note': self.internal_note,
        }
