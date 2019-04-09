# -*- coding: utf-8 -*-

from odoo import models, fields, api

from odoo.addons.mail.models.mail_template import format_date

class SaleOrder(models.Model):
    _inherit = 'sale.order'

    payment_ids = fields.Many2many('account.payment', 'sale_order_account_payment_rel', 'order_id', 'payment_id', string="Paiements", copy=False, readonly=True)
    of_payment_amount = fields.Float(compute='_compute_of_payment_amount')

    @api.depends('payment_ids')
    def _compute_of_payment_amount(self):
        for sale_order in self:
            sale_order.of_payment_amount = sum(sale_order.payment_ids.mapped('amount'))

    @api.multi
    def action_view_payments(self):
        action = self.env.ref('of_sale_payment.of_sale_payment_open_payments').read()[0]
        action['domain'] = [('order_ids', 'in', self._ids)]
        return action

    @api.multi
    def _of_get_printable_payments(self, order_lines):
        """
        Récupération des paiements liés à la commande si aucun autre paiement est affiché
        """
        result = super(SaleOrder, self)._of_get_printable_payments(order_lines)
        invoice_obj = self.env['account.invoice']
        account_move_line_obj = self.env['account.move.line']
        if not result:
            for payment in self.payment_ids:
                # Les paiements sont classés dans l'ordre chronologique
                move_line = account_move_line_obj.browse(payment['payment_id'])
                name = invoice_obj._of_get_payment_display(move_line)
                result.append((name, payment['amount']))
        return result

class AccountPayment(models.Model):
    _inherit = 'account.payment'

    order_ids = fields.Many2many('sale.order', 'sale_order_account_payment_rel', 'payment_id', 'order_id', string="Commandes client", copy=False, readonly=True)
    of_order_count = fields.Integer(compute='_compute_of_order_count')

    @api.depends('order_ids')
    def _compute_of_order_count(self):
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
                    for d, am in to_pay:
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

    @api.multi
    def assign_outstanding_credit(self, credit_aml_id):
        # A l'assignation d'un paiement à une facture, on le lie également aux bons de commande associés
        res = super(AccountInvoice, self).assign_outstanding_credit(credit_aml_id)

        credit_aml = self.env['account.move.line'].browse(credit_aml_id)
        if credit_aml.payment_id:
            order_ids = self.invoice_line_ids.mapped('sale_line_ids').mapped('order_id')._ids

            credit_aml.payment_id.write({'order_ids': [(4, order_id, None) for order_id in order_ids]})
        return res

class ResPartner(models.Model):
    _inherit = "res.partner"

    of_payment_ids = fields.One2many('account.payment', 'partner_id', string="Paiements")
    of_payment_total = fields.Float(compute="_compute_payment_total", string="Total des paiements")

    @api.depends('of_payment_ids')
    def _compute_payment_total(self):
        for partner in self:
            partner.of_payment_total = sum(partner.of_payment_ids.mapped('amount'))

    @api.multi
    def action_view_payments(self):
        action = self.env.ref('of_sale_payment.of_sale_payment_open_payments').read()[0]
        action['domain'] = [('partner_id', 'in', self._ids)]
        return action
