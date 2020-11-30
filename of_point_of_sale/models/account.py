# -*- coding: utf-8 -*-

from odoo import fields, models, api


class AccountJournal(models.Model):
    _inherit = 'account.journal'

    of_pos_payment_mode_ids = fields.Many2many(
        comodel_name='of.account.payment.mode', string=u"Mode de paiement associé au journal pour le point de vente")


class AccountPayment(models.Model):
    _inherit = 'account.payment'

    @api.model
    def create(self, values):
        if not values.get('of_payment_mode_id') and values.get('journal_id'):
            journal = self.env['account.journal'].browse(values.get('journal_id'))
            if journal.journal_user:
                corresponding_payment_mode_id = journal.of_pos_payment_mode_ids.filtered(
                    lambda pm: pm.company_id == self.env.user.company_id)
                if corresponding_payment_mode_id and corresponding_payment_mode_id[0]:
                    values.update({'of_payment_mode_id': corresponding_payment_mode_id[0].id})
        return super(AccountPayment, self).create(values)
