# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import UserError


class OfWizardInvoiceEditAccounts(models.TransientModel):
    _name = 'of.wizard.invoice.edit.accounts'

    line_ids = fields.One2many('of.wizard.invoice.edit.accounts.line', 'wizard_id')

    @api.model
    def default_get(self, fields_list):
        result = super(OfWizardInvoiceEditAccounts, self).default_get(fields_list)
        if 'line_ids' in fields_list:
            invoice = self.env['account.invoice'].browse(self._context['active_ids'])
            result['line_ids'] = [
                (0, 0, {
                    'invoice_line_id': line.id,
                    'account_id': line.account_id.id,
                    'quantity': line.quantity,
                    'price_unit': line.price_unit,
                    'price_subtotal': line.price_subtotal,
                })
                for line in invoice.invoice_line_ids
            ]
        return result

    def action_process(self):
        inv_obj = self.env['account.invoice']
        invoice = inv_obj.browse(self._context['active_ids'])

        old_line_accounts = invoice.invoice_line_ids.mapped('account_id')
        for line in self.line_ids:
            # On applique les nouveaux comptes aux lignes de facture.
            if line.account_id != line.invoice_line_id.account_id:
                line.invoice_line_id.account_id = line.account_id

        if not invoice.move_id:
            # Après tout, si quelqu'un veut utiliser l'outil pour une facture brouillon... pourquoi pas.
            return

        old_move_lines = self.env['account.move.line'].search(
            [('move_id', '=', invoice.move_id.id), ('account_id', 'in', old_line_accounts.ids)]
        )

        iml = invoice.invoice_line_move_line_get()
        company_currency = invoice.company_id.currency_id
        _, _, iml = invoice.with_context(lang=invoice.partner_id.lang).compute_invoice_totals(company_currency, iml)

        #  On vérifie la cohérence des données
        old_balance = sum(old_move_lines.mapped('debit')) - sum(old_move_lines.mapped('credit'))
        new_balance = sum(l['price'] for l in iml)
        if old_balance != new_balance:
            raise UserError(u"La pièce comptable semble ne pas correspondre à la facture.\n"
                            u"Total HT : %.02f vs %.02f" % (old_balance, new_balance))

        partner_id = invoice.partner_id.id
        line = [(0, 0, invoice.line_get_convert(l, partner_id)) for l in iml]
        line = invoice.group_lines(iml, line)
        # Pour pouvoir supprimer les anciennes lignes, il faut forcer l'état de la pièce en brouillon
        invoice.move_id.state = 'draft'
        # self.env.cr.execute("UPDATE account_move SET state='draft' WHERE id = %s" % (invoice.move_id.id, ))
        # Suppression des lignes via odoo pour les autres vérifications de sécurité (e.g. date de verrouillage)
        line += [(2, old_line.id) for old_line in old_move_lines]
        invoice.move_id.write({'line_ids': line})
        # On revalide la pièce, ce qui peut aussi lancer d'autres recalculs, comme les lignes analytiques
        invoice.move_id.post()


class OfWizardInvoiceEditAccountsLine(models.TransientModel):
    _name = 'of.wizard.invoice.edit.accounts.line'

    wizard_id = fields.Many2one('of.wizard.invoice.edit.accounts')
    invoice_line_id = fields.Many2one('account.invoice.line', string="Ligne de facture", readonly=True)
    account_id = fields.Many2one('account.account', string="Compte")
    quantity = fields.Float(string=u"Quantité", readonly=True)
    price_unit = fields.Float(string="Prix unitaire", readonly=True)
    price_subtotal = fields.Float(string="Montant", readonly=True)
