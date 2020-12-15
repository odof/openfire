# -*- coding: utf-8 -*-

import json

from odoo import api, fields, models, _
from odoo.tools import float_is_zero


class AccountPayment(models.Model):
    _name = 'account.payment'
    _inherit = ['account.payment', 'mail.thread']

    of_expected_deposit_date = fields.Date(string=u"Date de remise prévue")
    of_amount_total = fields.Monetary(
        string=u"Total", store=True, compute='_compute_of_amount_total',
        help=u"Montant Total dans la devise du paiement, négatif pour les règlements sortants.")

    # Ajout de la visibilité des champs dans le chatter
    partner_id = fields.Many2one(track_visibility='always')
    amount = fields.Monetary(track_visibility='always')
    state = fields.Selection(track_visibility='onchange')
    payment_type = fields.Selection(track_visibility='onchange')
    payment_date = fields.Date(track_visibility='onchange')

    # Champs utilisés pour la gestion des lettrages depuis le formulaire
    # Champs copiés/adaptés depuis account/models/account_invoice.py
    payment_move_line_ids = fields.Many2many(
        'account.move.line', string='Payment Move Lines', compute='_compute_payments')
    residual = fields.Monetary(string=u"Reste à lettrer", compute='_compute_residual', store=True)
    payments_widget = fields.Text(compute='_get_payment_info_json')
    outstanding_credits_debits_widget = fields.Text(compute='_get_outstanding_info_json')
    has_outstanding = fields.Boolean(compute='_get_outstanding_info_json')

    @api.one
    @api.depends(
        'state', 'currency_id',
        'move_line_ids.amount_residual',
        'move_line_ids.currency_id')
    def _compute_residual(self):
        residual = 0.0
        for line in self.sudo().move_line_ids:
            if line.account_id.internal_type in ('receivable', 'payable'):
                if line.currency_id == self.currency_id:
                    residual += line.amount_residual_currency if line.currency_id else line.amount_residual
                else:
                    from_currency = \
                        (line.currency_id and line.currency_id.with_context(date=line.date))\
                        or line.company_id.currency_id.with_context(date=line.date)
                    residual += from_currency.compute(line.amount_residual, self.currency_id)
        self.residual = abs(residual)

    @api.multi
    @api.depends('amount', 'currency_id', 'company_id', 'payment_date', 'payment_type')
    def _compute_of_amount_total(self):
        for rec in self:
            sign = -1 if rec.payment_type in ['outbound'] else 1
            rec.of_amount_total = rec.amount * sign

    @api.multi
    def button_invoices(self):
        """ (smart button facture sur les paiements)
        Choisit les vues en fonctions du type de partenaire
        """
        vals = super(AccountPayment, self).button_invoices()
        if self.partner_type == "customer":
            vals['views'] = [(self.env.ref('account.invoice_tree').id, 'tree'),
                             (self.env.ref('account.invoice_form').id, 'form')]
        elif self.partner_type == "supplier":
            vals['views'] = [(self.env.ref('account.invoice_supplier_tree').id, 'tree'),
                             (self.env.ref('account.invoice_supplier_form').id, 'form')]
        return vals

    def post(self):
        """Lors de la confirmation d'un paiement, rajoute le libellé sur toutes les écritures du paiement."""
        res = super(AccountPayment, self).post()
        for payment in self:
            payment.move_line_ids.write({
                'name': ((self.partner_id.name or self.partner_id.parent_id.name or '')[:30]
                         + " " + (self.communication or '')).strip()
            })

        # Ajout du paiement dans le RSE de la pièce comptable générée
        message = u"Pièce créée depuis : <a href=# data-oe-model=account.payment data-oe-id=%d>%s</a>"\
                  % (self.id, self.name)
        self.move_line_ids.mapped('move_id').message_post(body=message)

        return res

    def _get_move_vals(self, journal=None):
        """ Return dict to create the payment move
        """
        res = super(AccountPayment, self)._get_move_vals(journal=journal)
        res['ref'] = ((self.partner_id.name or self.partner_id.parent_id.name or '')[:30]
                      + " " + (self.communication or '')).strip()
        return res

    @api.model
    def create(self, vals):
        payment = super(AccountPayment, self).create(vals)
        if self._context.get('of_orig_payment_id'):
            # Ce paiement a été créé depuis un autre paiement, par le wizard du module of_l10n_fr_certification
            payment_orig = self.browse(self._context['of_orig_payment_id'])
            link_text = u"<a href=# data-oe-model=account.payment data-oe-id=%d>%s</a>"
            if self._context.get('of_orig_payment_operation') == 'refund':
                # Rempoursement de paiement
                message_orig = u"Paiement remboursé : "
                payment_name = u"Remboursement"
                message_new = u"Paiement créé depuis (remboursement) : "
            else:
                message_orig = u"Paiement modifié : "
                payment_name = u"Nouveau paiement"
                message_new = u"Paiement créé depuis (modification) : "
            payment_orig.message_post(message_orig + link_text % (payment.id, payment_name))
            payment.message_post(message_new + link_text % (payment_orig.id, payment_orig.name))

        elif self._context.get('default_invoice_ids') and payment.invoice_ids:
            invoice = payment.invoice_ids[0]
            message = u"Paiement créé depuis : <a href=# data-oe-model=account.invoice data-oe-id=%d>%s</a>"\
                      % (invoice.id, invoice.number)
            payment.message_post(body=message)
        return payment

    # Fonctions dédiées à la gestion des lettrages depuis le formulaire
    # Code essentiellement copié/adapté depuis account/models/account_invoice.py

    @api.one
    def _get_outstanding_info_json(self):
        self.outstanding_credits_debits_widget = json.dumps(False)
        if self.payment_type not in ('inbound', 'outbound'):
            return
        if self.state in ('draft', 'cancel'):
            return
        partner_account = self.move_line_ids.mapped('account_id')\
                              .filtered(lambda a: a.internal_type in ('receivable', 'payable'))
        if not partner_account:
            return
        domain = [
            ('account_id', 'in', partner_account.ids),
            ('partner_id', '=', self.env['res.partner']._find_accounting_partner(self.partner_id).id),
            ('reconciled', '=', False),
            '|',
              '&', ('amount_residual_currency', '!=', 0.0), ('currency_id', '!=', None),
              '&', ('amount_residual_currency', '=', 0.0),
                '&', ('currency_id', '=', None), ('amount_residual', '!=', 0.0)]
        if self.payment_type == 'outbound':
            domain.extend([('credit', '>', 0), ('debit', '=', 0)])
            type_payment = _('Outstanding credits')
        else:
            domain.extend([('credit', '=', 0), ('debit', '>', 0)])
            type_payment = _('Outstanding debits')
        info = {'title': '', 'outstanding': True, 'content': [], 'payment_id': self.id}
        lines = self.env['account.move.line'].search(domain)
        currency_id = self.currency_id
        if len(lines) != 0:
            for line in lines:
                # get the outstanding residual value in payment currency
                if line.currency_id and line.currency_id == self.currency_id:
                    amount_to_show = abs(line.amount_residual_currency)
                else:
                    amount_to_show = \
                        line.company_id.currency_id.with_context(date=line.date)\
                        .compute(abs(line.amount_residual), self.currency_id)
                if float_is_zero(amount_to_show, precision_rounding=self.currency_id.rounding):
                    continue
                info['content'].append({
                    'journal_name': line.journal_id.name + " - " + line.move_id.name,
                    'amount': amount_to_show,
                    'currency': currency_id.symbol,
                    'id': line.id,
                    'position': currency_id.position,
                    'digits': [69, self.currency_id.decimal_places],
                })
            info['title'] = type_payment
            self.outstanding_credits_debits_widget = json.dumps(info)
            self.has_outstanding = True

    @api.one
    @api.depends('move_line_ids.amount_residual')
    def _compute_payments(self):
        payment_lines = []
        for line in self.move_line_ids.filtered(lambda l: l.account_id.internal_type in ('receivable', 'payable')):
            payment_lines.extend(filter(None, [rp.credit_move_id.id for rp in line.matched_credit_ids]))
            payment_lines.extend(filter(None, [rp.debit_move_id.id for rp in line.matched_debit_ids]))
        self.payment_move_line_ids = self.env['account.move.line'].browse(list(set(payment_lines)))

    @api.one
    @api.depends('move_line_ids.amount_residual')
    def _get_payment_info_json(self):
        self.payments_widget = json.dumps(False)
        if self.payment_move_line_ids:
            info = {'title': _('Less Payment'), 'outstanding': False, 'content': []}
            currency_id = self.currency_id
            for payment in self.payment_move_line_ids:
                payment_currency_id = False
                if self.payment_type == 'outbound':
                    amount = sum(
                        [p.amount
                         for p in payment.matched_debit_ids
                         if p.debit_move_id in self.move_line_ids])
                    amount_currency = sum(
                        [p.amount_currency
                         for p in payment.matched_debit_ids
                         if p.debit_move_id in self.move_line_ids])
                    if payment.matched_debit_ids:
                        payment_currency_id = all(
                            [p.currency_id == payment.matched_debit_ids[0].currency_id
                             for p in payment.matched_debit_ids]
                        ) and payment.matched_debit_ids[0].currency_id or False
                elif self.payment_type == 'inbound':
                    amount = sum(
                        [p.amount
                         for p in payment.matched_credit_ids
                         if p.credit_move_id in self.move_line_ids])
                    amount_currency = sum(
                        [p.amount_currency
                         for p in payment.matched_credit_ids
                         if p.credit_move_id in self.move_line_ids])
                    if payment.matched_credit_ids:
                        payment_currency_id = all(
                            [p.currency_id == payment.matched_credit_ids[0].currency_id
                             for p in payment.matched_credit_ids]
                        ) and payment.matched_credit_ids[0].currency_id or False
                # get the payment value in payment currency
                if payment_currency_id and payment_currency_id == self.currency_id:
                    amount_to_show = amount_currency
                else:
                    amount_to_show = \
                        payment.company_id.currency_id.with_context(date=payment.date).compute(amount, self.currency_id)
                if float_is_zero(amount_to_show, precision_rounding=self.currency_id.rounding):
                    continue
                payment_ref = payment.move_id.name
                if payment.move_id.ref:
                    payment_ref += ' (' + payment.move_id.ref + ')'
                info['content'].append({
                    'name': payment.name,
                    'journal_name': payment.journal_id.name,
                    'amount': amount_to_show,
                    'currency': currency_id.symbol,
                    'digits': [69, currency_id.decimal_places],
                    'position': currency_id.position,
                    'date': payment.date,
                    'payment_id': payment.id,
                    'move_id': payment.move_id.id,
                    'ref': payment_ref,
                })
            self.payments_widget = json.dumps(info)

    @api.multi
    def assign_outstanding_credit(self, credit_aml_id):
        self.ensure_one()
        credit_aml = self.env['account.move.line'].browse(credit_aml_id)
        if not credit_aml.currency_id and self.currency_id != self.company_id.currency_id:
            credit_aml.with_context(allow_amount_currency=True, check_move_validity=False).write({
                'amount_currency': self.company_id.currency_id
                                       .with_context(date=credit_aml.date)
                                       .compute(credit_aml.balance, self.currency_id),
                'currency_id': self.currency_id.id})
        if credit_aml.invoice_id:
            self.write({'invoice_ids': [(4, credit_aml.invoice_id.id, None)]})
        move_lines = self.move_line_ids.filtered(lambda l: l.account_id.internal_type in ('receivable', 'payable'))
        return (move_lines + credit_aml).reconcile()
