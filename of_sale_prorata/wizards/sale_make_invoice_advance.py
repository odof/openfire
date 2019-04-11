# -*- coding: utf-8 -*-

from odoo import models, api
class SaleAdvancePaymentInv(models.TransientModel):
    _inherit = "sale.advance.payment.inv"

    @api.multi
    def _create_invoice(self, order, so_line, amount):
        invoice = super(SaleAdvancePaymentInv, self)._create_invoice(order, so_line, amount)

        # Ajout de la ligne de prorata, le cas échéant
        if order.of_prorata_percent:
            invoice.of_add_prorata_line(order.of_prorata_percent, order)

        # Ajout de la retenue de garantie, le cas échéant
        if order.of_retenue_garantie_pct:
            invoice.of_retenue_garantie_pct = order.of_retenue_garantie_pct

        return invoice
