# -*- coding: utf-8 -*-

import json
from odoo.tools import float_is_zero
from odoo import models, fields, api, _

class SaleOrder(models.Model):
    _inherit = 'sale.order'

    payment_ids = fields.Many2many('account.payment', 'sale_order_account_payment_rel', 'order_id', 'payment_id', string="Paiements", copy=False, readonly=True)
    of_payment_sum = fields.Float(compute='_compute_of_payment_sum')
    of_total_with_payment = fields.Float(compute="_compute_total_with_payment")
    of_print_payments = fields.Boolean('Impression des paiments')

    @api.depends('payment_ids')
    @api.multi
    def _compute_of_payment_sum(self):
        for sale_order in self:
            sale_order.of_payment_sum = sum(sale_order.payment_ids.mapped('amount'))

    def _invoices_state(self):
        for invoice in self.invoice_ids:
            if invoice.state != 'draft' and sum([payment[1] for payment in invoice._get_sum_payment()]) > 0.0:
                return True
        return False

    @api.multi
    def _get_sum_payment(self):
        total = []
        for invoice in self.invoice_ids:
            total += invoice._get_sum_payment()
        return total

    @api.depends('payment_ids', 'amount_total')
    @api.multi
    def _compute_total_with_payment(self):
        for sale_order in self:
            total_payments = 0.0
            if not sale_order._invoices_state():
                total_payments = sum(sale_order.payment_ids.mapped('amount'))
            else:
                for invoice in sale_order.invoice_ids:
                    total_payments += sum([payment[1] for payment in invoice._get_sum_payment()])
            sale_order.of_total_with_payment = max(sale_order.amount_total - total_payments, 0.0)

    @api.multi
    def action_view_payments(self):
        action = self.env.ref('of_sale_payment.of_sale_payment_open_payments').read()[0]
        action['domain'] = [('order_ids', 'in', self._ids)]
        return action

    @api.multi
    def button_payment(self):
        self.ensure_one()

class AccountPayment(models.Model):
    _inherit = 'account.payment'

    order_ids = fields.Many2many('sale.order', 'sale_order_account_payment_rel', 'payment_id', 'order_id', string="Commandes client", copy=False, readonly=True)
    of_order_count = fields.Integer(compute='_compute_order_count')

    @api.depends('order_ids')
    @api.multi
    def _compute_order_count(self):
        for payment in self:
            payment.of_order_count = len(payment.order_ids)

    @api.multi
    def action_view_orders(self):
        action = self.env.ref('of_sale_payment.of_sale_payment_open_sale_orders').read()[0]
        action['domain'] = [('payment_ids', 'in', self._ids)]
        return action

    @api.model
    def default_get(self, fields):
        rec = super(AccountPayment, self).default_get(fields)

        order_defaults = self.resolve_2many_commands('order_ids', rec.get('order_ids'), ['id'])
        invoice_defaults = self.resolve_2many_commands('invoice_ids', rec.get('invoice_ids'), ['id'])

        if invoice_defaults and not order_defaults:
            # Ajout du lien du paiements aux bons de commandes liés aux factures sélectionnées
            order_ids = set([order['id'] for order in order_defaults])
            invoice_ids = [invoice['id'] for invoice in invoice_defaults]
            invoices = self.env['account.invoice'].browse(invoice_ids)
            for invoice in invoices:
                for invoice_line in invoice.invoice_line_ids:
                    for order_line in invoice_line.sale_line_ids:
                        order_ids.add(order_line.order_id.id)
            rec['order_ids'] = [(6, 0, list(order_ids))]

        if order_defaults and len(order_defaults) == 1 and not invoice_defaults:
            order = self.env['sale.order'].browse(order_defaults[0]['id'])

            # Calcul du montant à proposer, qui sera par ordre de priorité :
            #  - en cas de facture non soldée, le total de leur balance
            #  - si des conditions de règlement sont définies, le reste à payer pour une échéance de plus
            #  - le reste à payer pour solder la commande
            amount = 0
            amount_paid = 0
            invoice_ids = []
            for invoice in order.invoice_ids:
                if invoice.state in ('open', 'paid'):
                    if invoice.residual:
                        amount += invoice.residual
                        invoice_ids.append(invoice.id)
                    else:
                        amount_paid += invoice.amount_total

            if not amount:
                partner_account_id = order.partner_id.property_account_receivable_id.id
                for payment in order.payment_ids:
                    if payment.state in ('posted', 'sent'):
                        for move_line in payment.move_line_ids:
                            if move_line.account_id.id == partner_account_id and not move_line.matched_debit_ids:
                                amount_paid += move_line.credit - move_line.debit

                if order.payment_term_id:
                    amount_to_pay = 0
                    to_pay = order.payment_term_id.compute(order.amount_total)[0]
                    for _, am in to_pay:
                        # Autorisation de 1€ d'ecart entre le montant payé et le montant dû
                        if amount_to_pay - 1 > amount_paid:
                            amount = round(amount_to_pay - amount_paid)
                            break
                        amount_to_pay += am
                    else:
                        amount = amount_to_pay - amount_paid
                else:
                    amount = order.amount_total - amount_paid

            amount = order.currency_id.round(max(amount, 0))

            if invoice_ids:
                rec['invoice_ids'] = [(6, 0, invoice_ids)]
            rec['communication'] = order.name
            rec['currency_id'] = order.currency_id.id
            rec['payment_type'] = 'inbound'
            rec['partner_type'] = 'customer'
            rec['partner_id'] = order.partner_id.id
            rec['amount'] = amount
        return rec

class AccountInvoice(models.Model):
    _inherit = 'account.invoice'

    # Seuls les paiements liés au bon de commande de la facture peuvent être utilisé sur la facture (demande d'Aymeric)
    # Quand on enregistre un paiement depuis une facture il est automatiquement lié aux bon de commandes
    # Surcharge de la fonction pour modifier domain
    @api.one
    def _get_outstanding_info_JSON(self):
        self.outstanding_credits_debits_widget = json.dumps(False)
        if self.state == 'open':
            domain = [('account_id', '=', self.account_id.id), ('partner_id', '=', self.env['res.partner']._find_accounting_partner(self.partner_id).id), ('reconciled', '=', False), ('amount_residual', '!=', 0.0), ('payment_id', 'in', self.invoice_line_ids.mapped('sale_line_ids').mapped('order_id').mapped('payment_ids').ids)]
            if self.type in ('out_invoice', 'in_refund'):
                domain.extend([('credit', '>', 0), ('debit', '=', 0)])
                type_payment = _('Outstanding credits')
            else:
                domain.extend([('credit', '=', 0), ('debit', '>', 0)])
                type_payment = _('Outstanding debits')
            info = {'title': '', 'outstanding': True, 'content': [], 'invoice_id': self.id}
            lines = self.env['account.move.line'].search(domain)
            currency_id = self.currency_id
            if len(lines) != 0:
                for line in lines:
                    # get the outstanding residual value in invoice currency
                    if line.currency_id and line.currency_id == self.currency_id:
                        amount_to_show = abs(line.amount_residual_currency)
                    else:
                        amount_to_show = line.company_id.currency_id.with_context(date=line.date).compute(abs(line.amount_residual), self.currency_id)
                    if float_is_zero(amount_to_show, precision_rounding=self.currency_id.rounding):
                        continue
                    info['content'].append({
                        'journal_name': line.ref or line.move_id.name,
                        'amount': amount_to_show,
                        'currency': currency_id.symbol,
                        'id': line.id,
                        'position': currency_id.position,
                        'digits': [69, self.currency_id.decimal_places],
                    })
                info['title'] = type_payment
                self.outstanding_credits_debits_widget = json.dumps(info)
                self.has_outstanding = True

    @api.multi
    def assign_outstanding_credit(self, credit_aml_id):
        # A l'assignation d'un paiement à une facture, on le lie également aux bons de commande associés
        res = super(AccountInvoice, self).assign_outstanding_credit(credit_aml_id)

        credit_aml = self.env['account.move.line'].browse(credit_aml_id)
        if credit_aml.payment_id:
            order_ids = set()
            for invoice_line in self.invoice_line_ids:
                for order_line in invoice_line.sale_line_ids:
                    order_ids.add(order_line.order_id.id)

            credit_aml.payment_id.write({'order_ids': [(4, order_id, None) for order_id in order_ids]})
        return res

    # Copie du code d'odoo pour l'affichage du montant lettré avec la facture (module account, account_invoice.py _get_payment_info_JSON)
    @api.multi
    def _get_sum_payment(self):
        total = []
        for invoice in self:
            for payment in invoice.payment_move_line_ids:
                payment_currency_id = False
                if invoice.type in ('out_invoice', 'in_refund'):
                    amount = sum([p.amount for p in payment.matched_debit_ids if p.debit_move_id in invoice.move_id.line_ids])
                    amount_currency = sum([p.amount_currency for p in payment.matched_debit_ids if p.debit_move_id in invoice.move_id.line_ids])
                    if payment.matched_debit_ids:
                        payment_currency_id = all([p.currency_id == payment.matched_debit_ids[0].currency_id for p in payment.matched_debit_ids]) and payment.matched_debit_ids[0].currency_id or False
                elif invoice.type in ('in_invoice', 'out_refund'):
                    amount = sum([p.amount for p in payment.matched_credit_ids if p.credit_move_id in invoice.move_id.line_ids])
                    amount_currency = sum([p.amount_currency for p in payment.matched_credit_ids if p.credit_move_id in invoice.move_id.line_ids])
                    if payment.matched_credit_ids:
                        payment_currency_id = all([p.currency_id == payment.matched_credit_ids[0].currency_id for p in payment.matched_credit_ids]) and payment.matched_credit_ids[0].currency_id or False
                if payment_currency_id and payment_currency_id == invoice.currency_id:
                    amount_to_show = amount_currency
                else:
                    amount_to_show = payment.company_id.currency_id.with_context(date=payment.date).compute(amount, invoice.currency_id)
                total.append((payment, amount_to_show))
        return total

class OfResPartner(models.Model):
    _inherit = "res.partner"

    of_payment_ids = fields.One2many('account.payment', 'partner_id', string="Paiements")
    of_payment_total = fields.Float(compute="_compute_payment_total", string="Nombre de paiement")

    @api.depends('of_payment_ids')
    @api.multi
    def _compute_payment_total(self):
        for partner in self:
            partner.of_payment_total = sum(partner.of_payment_ids.mapped('amount'))

    @api.multi
    def action_view_payments(self):
        action = self.env.ref('of_sale_payment.of_sale_payment_open_payments').read()[0]
        action['domain'] = [('partner_id', 'in', self._ids)]
        return action
