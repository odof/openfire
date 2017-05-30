# -*- coding: utf-8 -*-

from odoo import models, fields, api, _

class SaleOrder(models.Model):
    _inherit = 'sale.order'

    payment_ids = fields.Many2many('account.payment', 'sale_order_account_payment_rel', 'order_id', 'payment_id', string="Paiements", copy=False, readonly=True)

    @api.multi
    def button_payment(self):
        self.ensure_one()

class AccountPayment(models.Model):
    _inherit = 'account.payment'

    order_ids = fields.Many2many('sale.order', 'sale_order_account_payment_rel', 'payment_id', 'order_id', string="Commandes client", copy=False, readonly=True)

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
                    for _,am in to_pay:
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
            order_ids = set()
            for invoice_line in self.invoice_line_ids:
                for order_line in invoice_line.sale_line_ids:
                    order_ids.add(order_line.order_id.id)

            credit_aml.payment_id.write({'order_ids': [(4, order_id, None) for order_id in order_ids]})
        return res
