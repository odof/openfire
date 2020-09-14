# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError


class OfAccountPaymentBankDeposit(models.Model):
    _name = 'of.account.payment.bank.deposit'
    _description = 'Payment bank deposit'

    @api.multi
    def _get_default_payments(self):
        res = []
        if self._context.get('active_model', '') == 'account.payment':
            # Allow only payments that have not been already deposited
            payments = self.env['account.payment'].search(
                [('id', 'in', self._context['active_ids']), ('of_deposit_id', '=', False)])
            res = [(4, payment.id) for payment in payments]
        return res

    name = fields.Char('Deposit code', required=True, help='Deposit code')
    date = fields.Date('Date', required=True, default=fields.Date.context_today)
    payment_ids = fields.One2many(
        'account.payment', 'of_deposit_id', 'Payments', copy=False, default=_get_default_payments)
    payment_count = fields.Integer(string=u"Nombre de paiements", compute='_compute_payment_count')
    payment_total = fields.Float(string=u"Montant total des paiements", compute='_compute_payment_total')
    currency_id = fields.Many2one(
        comodel_name='res.currency', string='Devise', required=True,
        default=lambda self: self.env.user.company_id.currency_id)
    move_id = fields.Many2one('account.move', 'Account move', readonly=True, ondelete='restrict')
    state = fields.Selection([('draft', 'Unposted'), ('posted', 'Posted')], string='Status',
                             required=True, readonly=True, copy=False, default='draft')
    journal_id = fields.Many2one(
        'account.journal', 'Journal', required=True,
        domain="[('type', 'in', ('cash', 'bank')), ('of_allow_bank_deposit', '=', True)]")

    _order = 'date DESC'

    @api.depends('payment_ids')
    def _compute_payment_count(self):
        for rec in self:
            rec.payment_count = len(rec.payment_ids)

    @api.depends('payment_ids', 'payment_ids.amount')
    def _compute_payment_total(self):
        for rec in self:
            rec.payment_total = sum(rec.payment_ids.mapped('amount'))

    @api.multi
    def post(self):
        move_obj = self.env['account.move']
        move_line_obj = self.env['account.move.line'].with_context(check_move_validity=False)

        for rec in self:
            name = rec.name
            journal = rec.journal_id
            debit_account = journal.default_debit_account_id
            move_lines_dict = {}
            amount_total = 0
            for payment in rec.payment_ids:
                for move_line in payment.move_line_ids:
                    if move_line.reconciled:
                        continue
                    if payment.payment_type == 'inbound':
                        if move_line.debit == 0:
                            continue
                    elif payment.payment_type == 'outbound':
                        if move_line.credit == 0:
                            continue
                    if move_line.account_id in (debit_account, payment.writeoff_account_id):
                        continue

                    move_lines_dict.setdefault(move_line.account_id, []).append(move_line)
                    amount_total += move_line.debit - move_line.credit

            rec.state = 'posted'

            if amount_total == 0:
                continue

            move_data = {
                'journal_id': journal.id,
                'date': rec.date,
                'company_id': journal.company_id.id,
                'ref': _('Deposit %s') % (name,),
            }
            move = move_obj.create(move_data)

            move_line_obj.create({
                'move_id': move.id,
                'name': _('Deposit %s') % (name,),
                'account_id': debit_account.id,
                'debit': amount_total > 0 and amount_total,
                'credit': amount_total < 0 and -amount_total,
            })

            for account, move_lines in move_lines_dict.iteritems():
                if journal.of_bank_deposit_group_move:
                    amount = sum(move_line.debit - move_line.credit for move_line in move_lines)
                    if amount:
                        move_line = move_line_obj.create({
                            'move_id': move.id,
                            'name': _('Deposit %s') % (name,),
                            'account_id': account.id,
                            'credit': amount > 0 and amount,
                            'debit': amount < 0 and -amount,
                        })

                        move_line_ids = [ml.id for ml in move_lines] + [move_line.id]
                        move_lines = move_line_obj.browse(move_line_ids)
                else:
                    move_line_ids = []
                    for move_line in move_lines:
                        amount = move_line.debit - move_line.credit
                        if amount:
                            new_move_line = move_line_obj.create({
                                'move_id': move.id,
                                'name': _('%s / %s - Deposit %s') %
                                (move_line.partner_id.name,
                                 move_line.partner_id.with_context(force_company=move_line.payment_id.company_id.id).
                                 property_account_receivable_id.code,
                                 name),
                                'account_id': account.id,
                                'credit': amount > 0 and amount,
                                'debit': amount < 0 and -amount,
                                'partner_id': move_line.partner_id.id,
                            })

                            move_line_ids += [move_line.id, new_move_line.id]
                    move_lines = move_line_obj.browse(move_line_ids)
                move_lines.reconcile()
                move_lines.compute_full_after_batch_reconcile()

            move.post()
            rec.move_id = move.id
        return True

    @api.multi
    def cancel(self):
        for rec in self:
            if rec.move_id:  # move_id can be null when payments amount is 0
                rec.move_id.line_ids.remove_move_reconcile()
                move_id = rec.move_id
                rec.move_id = False
                move_id.button_cancel()
                move_id.unlink()
            rec.state = 'draft'
        return True

    @api.multi
    def unlink(self):
        if any(rec.state != 'draft' for rec in self):
            raise UserError(_("You can not delete a deposit that is already posted"))
        return super(OfAccountPaymentBankDeposit, self).unlink()

    @api.multi
    def _check_payment_ids(self, payment_data):
        if not payment_data:
            return
        ids = self._ids
        payments = self.resolve_2many_commands('payment_ids', payment_data, fields=['of_deposit_id', 'name'])
        if not payments:
            return

        if len(ids) > 1:
            raise UserError(_('You cannot set a payment for several deposits'))
        else:
            dep_id = ids and ids[0] or False

            for payment in payments:
                if payment['of_deposit_id'] and payment['of_deposit_id'][0] != dep_id:
                    raise UserError(_('Payment %s has already been deposited') % payment['name'])

    @api.model
    def create(self, vals):
        self._check_payment_ids(vals.get('payment_ids', False))
        return super(OfAccountPaymentBankDeposit, self).create(vals)

#    Uncomment this method to have an error message at the opening of the wizard when a payment is already deposited
#    The main drawback is that the user loses his selection of payments, so we prefer an error at the deposit creation

#     @api.model
#     def default_get(self, fields_list):
#         payment_ids = self._context.get('default_payment_ids', [])
#         payments = self.env['account.payment'].browse(payment_ids)
#         for payment in payments:
#             if payment.of_deposit_id:
#                 raise UserError(_('Payment %s has already been deposited') % payment.name)
#         return super(OfAccountPaymentBankDeposit, self).default_get(fields_list)


class AccountPayment(models.Model):
    _inherit = 'account.payment'

    of_deposit_id = fields.Many2one('of.account.payment.bank.deposit', 'Bank deposit', readonly=True, copy=False)


class AccountJournal(models.Model):
    _inherit = 'account.journal'

    @api.model_cr_context
    def _auto_init(self):
        cr = self._cr
        init = False
        if self._auto:
            cr.execute(
                "SELECT * FROM information_schema.columns "
                "WHERE table_name = '%s' AND column_name = 'of_allow_bank_deposit'" % (self._table,))
            init = not bool(cr.fetchall())

        res = super(AccountJournal, self)._auto_init()
        if init:
            cr.execute("UPDATE %s "
                       "SET of_allow_bank_deposit = True "
                       "WHERE type = 'bank'" % (self._table, ))
        return res

    of_bank_deposit_group_move = fields.Boolean(
        string=u"Grouper les écritures par compte lors d'une remise en banque", default=True)
    of_allow_bank_deposit = fields.Boolean(string=u"Autoriser les remises en banque")

    @api.onchange('type')
    def _onchange_type(self):
        super(AccountJournal, self)._onchange_type()
        if self.type == 'bank':
            self.of_allow_bank_deposit = True
        else:
            self.of_allow_bank_deposit = False