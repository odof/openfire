# -*- coding: utf-8 -*-

from odoo import api, models


class OfContractProduct(models.Model):
    _inherit = 'of.contract.product'

    @api.multi
    def copy_contract_line_products_vals(self):
        self.ensure_one()
        return {
            'product_id': self.product_id.id,
            'name': self.name,
            'price_unit': self.price_unit,
            'purchase_price': self.purchase_price,
            'quantity': self.quantity,
            'discount': self.discount,
            'tax_ids': [(4, tax.id) for tax in self.tax_ids],
            'account_analytic_id': self.account_analytic_id.id,
        }
