# -*- coding: utf-8 -*-

from odoo import api, fields, models


class AccountPayment(models.Model):
    _inherit = 'account.payment'

    of_expected_deposit_date = fields.Date(string=u"Date de remise prévue")

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