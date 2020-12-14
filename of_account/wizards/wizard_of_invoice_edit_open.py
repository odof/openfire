# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import UserError


class OfWizardInvoiceEditOpen(models.TransientModel):
    _name = 'of.wizard.invoice.edit.open'

    invoice_id = fields.Many2one(
        'account.invoice', string="Facture", required=True, default=lambda s: s.env.context.get('active_id'))
    inv_account_id = fields.Many2one('account.account', related='invoice_id.account_id')
    inv_date_due = fields.Date(related='invoice_id.date_due')
    inv_name = fields.Char(related='invoice_id.name')
    inv_partner_shipping_id = fields.Many2one('res.partner', related='invoice_id.partner_shipping_id')
    inv_user_id = fields.Many2one('res.users', related='invoice_id.user_id')
    line_ids = fields.One2many('of.wizard.invoice.edit.open.line', 'wizard_id')

    @api.model
    def default_get(self, fields_list):
        result = super(OfWizardInvoiceEditOpen, self).default_get(fields_list)
        if 'line_ids' in fields_list:
            invoice = self.env['account.invoice'].browse(self._context['active_ids'])
            result['line_ids'] = [
                (0, 0, {
                    'invoice_line_id': line.id,
                    'name': line.name,
                    'account_id': line.account_id.id,
                    'quantity': line.quantity,
                    'price_unit': line.price_unit,
                    'price_subtotal': line.price_subtotal,
                })
                for line in invoice.invoice_line_ids
            ]
        return result

    def action_dummy(self):
        pass

    def update_move_accounts(self, old_inv_account):
        inv_obj = self.env['account.invoice']
        move_line_obj = self.env['account.move.line']
        invoice = inv_obj.browse(self._context['active_ids'])

        old_line_accounts = invoice.invoice_line_ids.mapped('account_id')
        for line in self.line_ids:
            # On applique les nouveaux comptes aux lignes de facture.
            vals = {}
            if line.account_id != line.invoice_line_id.account_id:
                vals['account_id'] = line.account_id.id
            if line.name != line.invoice_line_id.name:
                vals['name'] = line.name
            if vals:
                line.invoice_line_id.write(vals)

        if not invoice.move_id:
            # Après tout, si quelqu'un veut utiliser l'outil pour une facture brouillon... pourquoi pas.
            return

        old_move_lines = move_line_obj.search(
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
        # Suppression des lignes via odoo pour les autres vérifications de sécurité (e.g. date de verrouillage)
        line += [(2, old_line.id) for old_line in old_move_lines]
        # Mise à jour du compte de tiers
        if old_inv_account != self.inv_account_id:
            if old_inv_account in old_line_accounts:
                raise UserError(u"Le compte de tiers est aussi présent sur une ligne de facture")
            line += [
                (1, move_line.id, {'account_id': self.inv_account_id.id})
                for move_line in move_line_obj.search(
                    [('move_id', '=', invoice.move_id.id), ('account_id', '=', old_inv_account.id)])
            ]
        invoice.move_id.write({'line_ids': line})

        # On revalide la pièce, ce qui peut aussi lancer d'autres recalculs, comme les lignes analytiques
        invoice.move_id.post()

    @api.model
    def create(self, vals):
        u"""
        Le wizard est créé lorsque l'utilisateur valide son application.
        On peut donc procéder ici à la modification des champs de la facture.
        Les champs related pointant sur des champs "readonly" de la facture, ceux-cis ne seront pas automatiquement
        mis à jour. Il faut appeler un write manuellement.
        """
        invoice = self.env['account.invoice'].browse(vals['invoice_id'])
        old_inv_account = invoice.account_id
        create_vals = {}
        inv_vals = {}
        for field, val in vals.iteritems():
            if field.startswith('inv_'):
                inv_field = field[4:]
                old_val = invoice._fields[inv_field].convert_to_write(invoice[inv_field], invoice)
                if val != old_val:
                    inv_vals[inv_field] = val
            else:
                create_vals[field] = val
        result = super(OfWizardInvoiceEditOpen, self).create(create_vals)
        result.invoice_id.write(inv_vals)
        result.update_move_accounts(old_inv_account)
        return result


class OfWizardInvoiceEditOpenLine(models.TransientModel):
    _name = 'of.wizard.invoice.edit.open.line'

    wizard_id = fields.Many2one('of.wizard.invoice.edit.open')
    invoice_line_id = fields.Many2one('account.invoice.line', string="Ligne de facture", readonly=True)
    name = fields.Text(string=u"Libellé")
    account_id = fields.Many2one('account.account', string="Compte")
    quantity = fields.Float(string=u"Quantité", readonly=True)
    price_unit = fields.Float(string="Prix unitaire", readonly=True)
    price_subtotal = fields.Float(string="Montant", readonly=True)
