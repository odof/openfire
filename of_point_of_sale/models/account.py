# -*- coding: utf-8 -*-

from odoo import fields, models, api


class AccountJournal(models.Model):
    _inherit = 'account.journal'

    of_pos_payment_mode_id = fields.Many2one(
        comodel_name='of.account.payment.mode', string=u"Mode de paiement associé au journal pour le point de vente")


class AccountPayment(models.Model):
    _inherit = 'account.payment'

    @api.model
    def create(self, values):
        if not values.get('of_payment_mode_id') and values.get('journal_id'):
            journal = self.env['account.journal'].browse(values.get('journal_id'))
            if journal.journal_user:
                values.update({'of_payment_mode_id': journal.of_pos_payment_mode_id.id})
        return super(AccountPayment, self).create(values)
