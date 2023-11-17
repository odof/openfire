# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
# -*- coding: utf-8 -*-

from odoo import models, fields, api, _


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    @api.multi
    def call_popup(self):
        difference = 0
        if not self.of_sale_type_id.invoice_info_exclusion:
            difference = self.partner_id.get_remaining_pending_amount(additional_amount=self.amount_total)
        if difference < 0:
            wizard_id = self.env['of.popup.warning'].create({
                'message': u"L'encours maximum de %s est dépassé de %.2f" % (self.partner_id.name, abs(difference))
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



