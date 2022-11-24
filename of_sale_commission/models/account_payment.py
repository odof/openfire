# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models, api


class AccountPayment(models.Model):
    _inherit = "account.payment"

    @api.multi
    def write(self, vals):
        orders = self.env['sale.order']
        if 'order_ids' in vals:
            orders = self.mapped('order_ids')
        res = super(AccountPayment, self).write(vals)
        if 'order_ids' in vals or 'active' in vals or 'state' in vals:
            orders |= self.mapped('order_ids')
        if orders:
            orders.of_verif_acomptes()
        return res
