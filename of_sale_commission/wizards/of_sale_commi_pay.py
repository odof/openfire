# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models, fields, api


class OFSaleCommiPay(models.TransientModel):
    """
    This wizard will confirm paid all the selected to_pay commis
    """
    _name = 'of.sale.commi.pay'
    _description = "Confirm paid the selected to_pay commis"

    @api.model
    def _default_draft(self):
        return self._check_state(('draft', ))

    @api.model
    def _default_cancel(self):
        return self._check_state(('cancel', ))

    @api.model
    def _default_paid(self):
        return self._check_state(('paid', 'paid_cancel'))

    draft = fields.Boolean(default=lambda self: self._default_draft())
    cancel = fields.Boolean(default=lambda self: self._default_cancel())
    paid = fields.Boolean(default=lambda self: self._default_paid())
    date = fields.Date(string='Date de paiement', required=True, default=fields.Date.today)

    @api.model
    def _check_state(self, states):
        commis = self.env['of.sale.commi'].browse(self._context.get('active_ids', []))
        return commis.filtered(lambda commi: commi.state in states)

    @api.multi
    def confirmer_paiement(self):
        commi_obj = self.env['of.sale.commi']
        commis = commi_obj.browse(self._context.get('active_ids', []))
        to_pay = [commi_obj, commi_obj]
        to_cancel = [commi_obj, commi_obj]
        for commi in commis:
            if commi.state in ('draft', 'to_pay'):
                to_pay[not commi.date_valid] |= commi
            elif commi.state == 'to_cancel':
                to_cancel[not commi.date_valid] |= commi
        to_pay[0].write({'state': 'paid', 'date_paiement': self.date})
        to_pay[1].write({'state': 'paid', 'date_paiement': self.date, 'date_valid': self.date})
        to_cancel[0].write({'state': 'paid_cancel', 'date_paiement': self.date})
        to_cancel[1].write({'state': 'paid_cancel', 'date_paiement': self.date, 'date_valid': self.date})
