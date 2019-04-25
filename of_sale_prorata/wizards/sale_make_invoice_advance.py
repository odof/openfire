# -*- coding: utf-8 -*-

from odoo import models, api
class SaleAdvancePaymentInv(models.TransientModel):
    _inherit = "sale.advance.payment.inv"

    @api.multi
    def _create_invoice(self, order, so_line, amount):
        invoice = super(SaleAdvancePaymentInv, self)._create_invoice(order, so_line, amount)

        # Ajout de la retenue de garantie, le cas échéant
        # La retenue de garantie se calcule avant l'application du prorata
        if order.of_retenue_garantie_pct:
            # La retenue de garantie se calcule sur le montant TTC, il faut donc calculer les taxes au préalable
            # invoice.compute_taxes()
            invoice.of_add_retenue_line(order.of_retenue_garantie_pct, order)

        # Ajout de la ligne de prorata, le cas échéant
        if order.of_prorata_percent:
            invoice.of_add_prorata_line(order.of_prorata_percent, order)

        return invoice
