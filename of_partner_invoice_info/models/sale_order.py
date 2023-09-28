# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
# -*- coding: utf-8 -*-

from odoo import models, fields, api, _


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    @api.multi
    def call_popup(self):
        difference = 0.0
        if self.partner_id.of_invoice_balance_max < (self.amount_total + self.partner_id.of_sale_order_to_invoice_amount
                                                     + self.partner_id.of_invoice_balance_total):
            difference = ((self.amount_total+self.partner_id.of_sale_order_to_invoice_amount +
                           self.partner_id.of_invoice_balance_total) - self.partner_id.of_invoice_balance_max)
            wizard_id = self.env['of.popup.warning'].create({
                'message': u"L'encours maximum de %s est dépassé de %.2f" % (self.partner_id.name, difference)
            })
            return {
                'type': 'ir.actions.act_window',
                'name': "Avertissement",
                'res_model': 'of.popup.warning',
                'res_id': wizard_id.id,
                'view_type': 'form',
                'view_mode': 'form',
                'target': 'new',
                'context': {'sale_order': self.id, 'difference': difference},
            }
        else:
            return self.action_verification_confirm()



