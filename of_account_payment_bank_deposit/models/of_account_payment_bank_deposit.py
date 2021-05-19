# -*- coding: utf-8 -*-

from odoo import models, fields, api, _, SUPERUSER_ID
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
            # On contrôle qu'il n'y ait pas différents modes de paiement dans la remise
            if len(rec.payment_ids.mapped('of_payment_mode_id')) > 1:
                raise UserError(_("You cannot validate a deposit including different payment method!"))
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
                move_id.with_context(of_cancel_payment_bank_deposit=True).button_cancel()
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
    of_cancel_moves = fields.Boolean(string=u"Autoriser l'annulation d'écritures (banque)")

    @api.onchange('type')
    def _onchange_type(self):
        super(AccountJournal, self)._onchange_type()
        if self.type == 'bank':
            self.of_allow_bank_deposit = True
        else:
            self.of_allow_bank_deposit = False
        self.update_posted = self.type in ('purchase', 'cash', 'bank', 'general')
        self.of_cancel_moves = False

    @api.onchange('update_posted')
    def _onchange_update_posted(self):
        if not self.update_posted:
            self.of_cancel_moves = False

    @api.onchange('of_allow_bank_deposit')
    def _onchange_of_allow_bank_deposit(self):
        self.update_posted = self.of_allow_bank_deposit

    @api.onchange('of_cancel_moves')
    def _onchange_of_cancel_moves(self):
        if self.of_cancel_moves:
            self.update_posted = True

    @api.multi
    def of_check_edit_updateable(self, vals):
        u"""
        Annule et remplace la fonction définie dans of_account.
        """
        if self._uid == SUPERUSER_ID:
            # L'admin a tous les droits. Pas d'erreur, on laisse les paramètres choisis.
            return False, {}
        error_msg = u"Vous ne pouvez pas autoriser la modification des écritures comptables sur un journal de ce type"
        error = False
        force_vals = {}
        if vals.get('of_cancel_moves'):
            # Ce champ ne peut jamais être forcé à vrai par un utilisateur autre que l'admin.
            error = True
        elif vals.get('update_posted'):
            # Modification manuelle de l'utilisateur.
            # Normalement, un readonly empêche de faire n'importe quoi.
            # Les tests suivants permettent d'éviter qu'un utilisateur passe outre ce readonly.

            # Séparation des journaux par type
            type_journals = {}
            if 'type' in vals:
                type_journals[vals['type']] = self
            elif self:
                default_journal = self.env['account.journal']
                for journal in self:
                    type_journals[journal.type] = type_journals.get(journal.type, default_journal) | journal
            else:
                type_journals[self.default_get(['type'])['type']] = self

            if 'sale' in type_journals:
                # Interdiction d'annuler les écritures pour un journal de ventes
                error = True
            elif 'bank' in type_journals or 'cash' in type_journals:
                # Un journal de banque/liquidités ne peut autoriser l'annulation d'écritures que si il autorise
                # la remise en banque. Dans ce cas, c'est le champ of_cancel_moves qui prendra le relai pour interdire
                # l'annulation des écritures de paiements.
                if 'of_allow_bank_deposit' in vals:
                    error = not vals['of_allow_bank_deposit']
                elif self:
                    error = self.filtered(lambda o: not o.of_allow_bank_deposit)
                else:
                    error = not self.default_get(['of_allow_bank_deposit'])['of_allow_bank_deposit']
        elif 'type' in vals:
            # Lors du changement de type d'un journal, le champ update_posted peut être à vrai
            #   et ne pas réussir à passer à faux car le champ est devenu readonly.
            # On s'assure donc de forcer cette valeur
            force = False
            if vals['type'] == 'sale':
                force = True
            elif vals['type'] in ('bank', 'cash'):
                force_vals['of_cancel_moves'] = False
                if 'of_allow_bank_deposit' in vals:
                    force = not vals['of_allow_bank_deposit']
                elif self:
                    force = self.filtered(lambda o: not o.of_allow_bank_deposit)
                else:
                    force = not self.default_get(['of_allow_bank_deposit'])['of_allow_bank_deposit']
            if force:
                force_vals['update_posted'] = False
        elif 'of_allow_bank_deposit' in vals:
            force_vals['of_cancel_moves'] = False
            if not vals['of_allow_bank_deposit']:
                force_vals['update_posted'] = False
        return error and error_msg or "", force_vals
