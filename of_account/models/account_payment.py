# -*- coding: utf-8 -*-

from odoo import api, fields, models


class AccountPayment(models.Model):
    _name = "account.payment"
    _inherit = ['account.payment', 'mail.thread']

    of_expected_deposit_date = fields.Date(string=u"Date de remise prévue")
    # Ajout de la visibilité des champs dans le chatter
    partner_id = fields.Many2one(track_visibility='always')
    amount = fields.Monetary(track_visibility='always')
    state = fields.Selection(track_visibility='onchange')
    payment_type = fields.Selection(track_visibility='onchange')
    payment_date = fields.Date(track_visibility='onchange')

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
        """Lors d'un lettrage d'un paiement, rajoute le libellé sur toutes les écritures du paiement."""
        res = super(AccountPayment, self).post()
        client_line = self.move_line_ids.filtered(lambda line: line.credit > 0)
        if client_line.name == _("Customer Payment"):
            self.move_line_ids.write({"name": (
                (self.partner_id.name or self.partner_id.parent_id.name or '')[:30]
                + " "
                + (self.communication or '')).strip()})  # Permet d'avoir toutes les lignes avec le même libellé
        else:
            self.move_line_ids.write({"name": client_line.name})
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
