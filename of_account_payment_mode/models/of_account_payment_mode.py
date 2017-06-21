# -*- encoding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

import traceback

class OfAccountPaymentMode(models.Model):
    _name = 'of.account.payment.mode'
    _description = 'Payment mode'

    name = fields.Char('Name', required=True, help='Mode of Payment')
    journal_id = fields.Many2one('account.journal', 'Journal', domain=[('type', 'in', ('bank', 'cash'))],
                                 required=True, help='Bank or Cash Journal for the Payment Mode')
    company_id = fields.Many2one('res.company', 'Company', required=True)
    partner_id = fields.Many2one(related='company_id.partner_id', string='Partner', store=True)
    journal_type = fields.Selection(related='journal_id.type', string='Type', readonly=True)

    @api.model_cr_context
    def _auto_init(self):
        '''
        Create one payment mode by cash/bank journal
        '''
        cr = self._cr
        cr.execute("SELECT * FROM information_schema.tables WHERE table_name = '%s'" % (self._table,))
        exists = bool(cr.fetchall())
        res = super(OfAccountPaymentMode, self)._auto_init()
        if not exists:
            cr.execute("INSERT INTO %s (name, journal_id, company_id, partner_id)\n"
                       "SELECT j.name, j.id, j.company_id, c.partner_id\n"
                       "FROM account_journal AS j\n"
                       "LEFT JOIN res_company AS c ON c.id=j.company_id\n"
                       "WHERE j.type IN ('bank','cash')" % (self._table,))
        return res

class AccountAbstractPayment(models.AbstractModel):
    _inherit = "account.abstract.payment"

    of_payment_mode_id = fields.Many2one('of.account.payment.mode', string='Payment mode', required=True)
    journal_id = fields.Many2one(related='of_payment_mode_id.journal_id', string='Payment Journal', store=True)

    @api.model_cr_context
    def _auto_init(self):
        cr = self._cr
        init_payment_mode = False
        if self._auto:
            cr.execute("SELECT * FROM information_schema.columns WHERE table_name = '%s' AND column_name = 'of_payment_mode_id'" % (self._table,))
            init_payment_mode = not bool(cr.fetchall())

        res = super(AccountAbstractPayment, self)._auto_init()
        if init_payment_mode:
            # Use self.pool as self.env is not yet defined
            comodel_table = self.pool[self._fields['of_payment_mode_id'].comodel_name]._table
            cr.execute("UPDATE %s AS p SET of_payment_mode_id = m.id\n"
                       "FROM %s AS m\n"
                       "WHERE m.journal_id = p.journal_id" % (self._table, comodel_table))
        return res

    @api.model
    def create(self, vals):
        '''
        Allow creation of payments with account journal instead of payment mode.
        In this case, the traceback is printed in logs.
        '''
        try:
            if 'journal_id' in vals and 'of_payment_mode_id' not in vals:
                of_payment_modes = self.env['of.account.payment.mode'].search([('journal_id', '=', vals['journal_id'])], limit=1)
                del vals['journal_id']
                if of_payment_modes:
                    vals['of_payment_mode_id'] = of_payment_modes._ids[0]
                    raise ValidationError(_("Creating payment with account journal instead of payment mode."))
        except ValidationError:
            traceback.print_exc()
        finally:
            return super(AccountAbstractPayment, self).create(vals)

class AccountRegisterPayments(models.TransientModel):
    _name = "account.register.payments"
    _inherit = ["account.register.payments", "account.abstract.payment"]

    def get_payment_vals(self):
        res = super(AccountRegisterPayments, self).get_payment_vals()
        del res['journal_id']
        res['of_payment_mode_id'] = self.of_payment_mode_id.id
        return res

class AccountPayment(models.Model):
    _name = "account.payment"
    _inherit = ["account.payment", "account.abstract.payment"]
