# -*- coding: utf-8 -*-

from odoo import fields, models, api


class AccountJournal(models.Model):
    _inherit = 'account.journal'

    of_pos_payment_mode_ids = fields.Many2many(
        comodel_name='of.account.payment.mode', string=u"Mode de paiement associé au journal pour le point de vente")


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    @api.model
    def create(self, values):
        # Si le context check_account_tax est présent
        if self._context.get('check_account_tax'):

            # On regarde si un account_id peut être redéfinie par ses taxes
            if values.get('account_id') and values.get('tax_ids'):

                income_account = values.get('account_id')
                account = self.env['account.account'].browse(income_account)
                tax_ids = values.get('tax_ids')

                for tax_id in tax_ids[0][2]:
                    # On récupère la taxe et le compte
                    tax = self.env['account.tax'].browse(tax_id)

                    # On regarde si le compte doit être réaffecté à un nouveau compte et on le rajoute dans values
                    income_account = tax.map_account(account).id
                    values['account_id'] = income_account

        return super(AccountMoveLine, self).create(values)


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
