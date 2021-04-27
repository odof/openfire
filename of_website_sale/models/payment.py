# -*- coding: utf-8 -*-

from odoo import models, fields, api


class PaymentAcquirer(models.Model):
    _inherit = 'payment.acquirer'

    of_payment_mode_id = fields.Many2one(comodel_name='of.account.payment.mode', string=u'Mode de paiment')

    @api.onchange('journal_id')
    def _onchange_journal_id(self):
        self.of_payment_mode_id = False


class PaymentTransaction(models.Model):
    _inherit = 'payment.transaction'

    def _generate_and_pay_invoice(self, tx, acquirer_name):
        return super(PaymentTransaction, self.with_context(of_payment_mode_id=tx.acquirer_id.of_payment_mode_id.id)).\
            _generate_and_pay_invoice(tx, acquirer_name)


class AccountAbstractPayment(models.AbstractModel):
    _inherit = 'account.abstract.payment'

    @api.model
    def create(self, vals):
        if self._context.get('of_payment_mode_id') and 'of_payment_mode_id' not in vals:
            vals['of_payment_mode_id'] = self._context.get('of_payment_mode_id')
        return super(AccountAbstractPayment, self).create(vals)
