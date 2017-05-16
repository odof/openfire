# -*- encoding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

class OfAccountPaymentBankDeposit(models.Model):
    _name = 'of.account.payment.bank.deposit'
    _description = 'Payment bank deposit'

    @api.multi
    def _get_default_payments(self):
        res = []
        if self._context.get('active_model', '') == 'account.payment':
            # Allow only payments that have not been already deposited
            payments = self.env['account.payment'].search([('id', 'in', self._context['active_ids']), ('of_deposit_id', '=', False)])
            res = [(4,payment.id) for payment in payments]
        return res

    name = fields.Char('Deposit code', required=True, help='Deposit code')
    date = fields.Date('Date', required=True, default=fields.Date.context_today)
    payment_ids = fields.One2many('account.payment', 'of_deposit_id', 'Payments', copy=False, default=_get_default_payments)
    move_id = fields.Many2one('account.move', 'Account move', readonly=True, ondelete='restrict')
    state = fields.Selection([('draft', 'Unposted'), ('posted', 'Posted')], string='Status',
                             required=True, readonly=True, copy=False, default='draft')
    journal_id = fields.Many2one('account.journal', 'Journal', required=True)

    _order = 'date DESC'

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
                'date'      : rec.date,
                'company_id': journal.company_id.id,
            }
            move = move_obj.create(move_data)

            move_line_obj.create({
                'move_id'   : move.id,
                'name'      : _('Deposit %s') % (name,),
                'account_id': debit_account.id,
                'debit'     : amount_total > 0 and amount_total,
                'credit'    : amount_total < 0 and -amount_total,
            })

            for account, move_lines in move_lines_dict.iteritems():
                amount = sum(move_line.debit - move_line.credit for move_line in move_lines)
                if amount:
                    move_line = move_line_obj.create({
                        'move_id'   : move.id,
                        'name'      : _('Deposit %s') % (name,),
                        'account_id': account.id,
                        'credit'    : amount > 0 and amount,
                        'debit'     : amount < 0 and -amount,
                    })

                    move_line_ids = [ml.id for ml in move_lines] + [move_line.id]
                    move_lines = move_line_obj.browse(move_line_ids)
                move_lines.reconcile()
                move_lines.compute_full_after_batch_reconcile()

            move.post()
            rec.move_id = move.id
        return True

    @api.multi
    def cancel(self):
        for rec in self:
            if rec.move_id: # move_id can be null when payments amount is 0
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
        payments = self.resolve_2many_commands('payment_ids', payment_data, fields=['of_deposit_id','name'])
        if not payments:
            return

        if len(ids) > 1:
            raise UserError(_('You cannot set a payment for several deposits'))
        else:
            dep_id = ids and ids[0] or False

            for payment in payments:
                if payment['of_deposit_id'] and payment['of_deposit_id'][0]!=dep_id:
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
