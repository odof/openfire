# -*- coding: utf-8 -*-

from odoo import api, fields, models


class PosOrder(models.Model):
    _inherit = "pos.order"

    @api.multi
    def action_pos_order_invoice(self):
        res = super(PosOrder, self).action_pos_order_invoice()

        # Lors d'une facturation depuis le point de vente, le onchange_tax_ids n'est pas déclenché, du coup on l'appelle
        for order in self:
            if order.invoice_id:
                for line in order.invoice_id.invoice_line_ids:
                    line.onchange_tax_ids()

        return res

    def _prepare_bank_statement_line_payment_values(self, data):
        self.partner_id.update_account()
        return super(PosOrder, self)._prepare_bank_statement_line_payment_values(data)
