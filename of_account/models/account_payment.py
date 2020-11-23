# -*- coding: utf-8 -*-

from odoo import api, fields, models


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
