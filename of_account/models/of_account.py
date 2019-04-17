# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import UserError

NEGATIVE_TERM_OPERATORS = ('!=', 'not like', 'not ilike', 'not in')

class AccountConfigSettings(models.TransientModel):
    _inherit = 'account.config.settings'

    # Paramètre de la date d'échéance des factures
    of_date_due = fields.Selection([(0, u"Date d'échéance en fonction des conditions de règlement"),
                                    (1, u"Modification manuelle de la date d'échéance possible (non recalcul suivant conditions de règlement si date déjà renseignée)")], string=u"(OF) Date d'échéance")

    @api.multi
    def set_of_date_due_defaults(self):
        return self.env['ir.values'].sudo().set_default('account.config.settings', 'of_date_due', self.of_date_due)

class AccountInvoice(models.Model):
    _inherit = "account.invoice"

    of_etiquette_partenaire_ids = fields.Many2many('res.partner.category', related='partner_id.category_id', string=u"Étiquettes client")

    # Date d'échéance des factures
    # Surcharge de la méthode pour permettre la comparaison avec le paramètrage du mode de calcul de la date d'échéance (manuel/auto).
    @api.onchange('payment_term_id', 'date_invoice')
    def _onchange_payment_term_date_invoice(self):
        param_date_due = self.env['ir.values'].get_default('account.config.settings', 'of_date_due')
        date_invoice = self.date_invoice
        if not date_invoice:
            date_invoice = fields.Date.context_today(self)
        if not self.payment_term_id:
            # Quand pas de condition de règlement définie
            if (param_date_due and not self.date_due) or not param_date_due:  # On rajoute la vérification pour permettre de modifier manuellement la date d'échéance.
                self.date_due = self.date_due or self.date_invoice
        else:
            pterm = self.payment_term_id
            pterm_list = pterm.with_context(currency_id=self.company_id.currency_id.id).compute(value=1, date_ref=date_invoice)[0]
            if (param_date_due and not self.date_due) or not param_date_due:  # On rajoute la vérification pour permettre de modifier manuellement la date d'échéance.
                self.date_due = max(line[0] for line in pterm_list)

    @api.multi
    def action_invoice_open(self):
        """Mettre le libellé des écritures comptables d'une facture avec nom client (30 1er caractères) + no facture"""
        res = super(AccountInvoice, self).action_invoice_open()
        ref = (self.partner_id.name or self.partner_id.parent_id.name or '')[:30] + ' ' + self.number
        self.move_id.line_ids.write({'name': ref})
        self.move_id.write({'ref': ref})
        return res

    @api.multi
    def write(self, vals):
        if 'tax_line_ids' in vals:
            # Lorsque les lignes de taxes sont changées / ajoutés sur une facture elles doivent toutes être
            # recréées, il faut donc unlink toutes les lignes qui ne sont pas des codes 0 (create)
            lines_to_keep = []
            for line in vals['tax_line_ids']:
                if line[0] == 0:
                    lines_to_keep.append(line)
            if lines_to_keep:
                vals['tax_line_ids'] = [(5, )] + lines_to_keep
        return super(AccountInvoice, self).write(vals)

class AccountAccount(models.Model):
    _inherit = "account.account"

    of_account_counterpart_id = fields.Many2one('account.account', string="Compte de contrepartie")

class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    @api.model
    def default_get(self, fields_list):
        def get_line_account(line):
            account_id = line['account_id']
            if not account_id:
                return False
            if isinstance(account_id, tuple):
                # Si la ligne existe en db account_id vaut (id, name), sinon c'est un id simple
                account_id = account_id[0]
            return account_obj.browse(account_id)
        journal_obj = self.env['account.journal']
        account_obj = self.env['account.account']

        result = super(AccountMoveLine, self).default_get(fields_list)

        lines = self._context.get('line_ids')
        journal_id = self._context.get('journal_id')
        if not journal_id or not lines:
            return result

        lines = self.env['account.move'].resolve_2many_commands('line_ids', lines, ('account_id', 'debit', 'credit', 'date_maturity'))
        journal = journal_obj.browse(journal_id)
        if journal.type in ('bank', 'cash'):  # pièce comptable de banque ou de caisse
            if len(lines) == 1:
                account = get_line_account(lines[0])
                if account and account.user_type_id.type in ('payable', 'receivable'):
                    if account.user_type_id.type == 'payable':
                        account = journal.default_credit_account_id
                    else:
                        account = journal.default_debit_account_id
                    result.update({
                        'account_id': account and account.id or False,
                        'debit': lines[0]['credit'],
                        'credit': lines[0]['debit'],
                        'date_maturity': lines[0]['date_maturity'],
                    })
        elif journal.type == 'purchase':  # pièce comptable fournisseur
            tax_type = 'purchase'
            len_lines = len(lines)
            if len_lines in (1, 2):
                # resolve_2many_commands ne préserve pas l'ordre des lignes
                # Le nouvel est ordre est [nouvelles lignes (code 0), autres lignes (déjà en DB)]
                # L'ordre est conservé à l'intérieur de ces deux sous-sections
                if lines[-1].get('id') and self._context['line_ids'][-1][0] == 0:
                    lines = lines[::-1]

                account = get_line_account(lines[-1])
                if account:
                    for tax in (account.of_account_counterpart_id.tax_ids if len_lines == 1 else account.tax_ids):
                        if tax.type_tax_use == tax_type:
                            break
                    else:
                        tax = False
                    if tax or len_lines == 1:
                        tax_amount = tax and tax.amount or 0
                        account = account.of_account_counterpart_id if len_lines == 1 else tax.account_id
                        result.update({
                            'account_id': account and account.id or False,
                            'debit': lines[0]['credit'] / (100 + tax_amount) * (100 if len_lines == 1 else tax_amount),
                            'credit': lines[0]['debit'] / (100 + tax_amount) * (100 if len_lines == 1 else tax_amount),
                            'date_maturity': lines[0]['date_maturity'],
                        })
        return result

    def reconcile(self, writeoff_acc_id=False, writeoff_journal_id=False):
        """Mettre le libellé des écritures comptables d'un paiement avec nom client (30 1er caractères) + no facture"""
        res = super(AccountMoveLine, self).reconcile(writeoff_acc_id=writeoff_acc_id, writeoff_journal_id=writeoff_journal_id)
        filt = self.filtered(lambda line: (line.reconciled or (line.matched_debit_ids and len(line.matched_debit_ids) == 1)) and line.payment_id)
        for line in filt:
            line_ids = self.env['account.move.line']
            if line.account_id.reconcile:
                for reconciled_lines in line.matched_debit_ids:
                    line_ids += reconciled_lines.debit_move_id
                invoice_ids = line_ids.mapped('invoice_id')
                try:
                    line.move_id.write({'ref': line.payment_id.communication or ''})
                except UserError:
                    # Avec le module OCA des verrouillages d'écritures, le write peut générer une erreur
                    # Il ne faut pas qu'elle soit bloquante pour les lettrages
                    pass
                if len(invoice_ids) == 1:
                    name_infos = [(invoice_ids.partner_id.name or invoice_ids.partner_id.parent_id.name or '')[:30], invoice_ids.number]
                    name = (' ').join([text for text in name_infos if text])
                    line.move_id.line_ids.with_context(check_move_validity=False).write({'name': name})
        return res

    # Lors d'une saisie d'une pièce comptable, pour préremplir le compte de tiers du partenaire saisi.
    @api.onchange('partner_id')
    def _onchange_partner_id(self):
        if self.partner_id and not self.account_id:
            if self.journal_id.type == 'sale': # Est un journal de vente, on prend le compte de tiers client.
                self.account_id = self.partner_id.property_account_receivable_id
            elif self.journal_id.type == 'purchase': # Est un journal d'achat, on prend le compte de tiers fournisseur.
                self.account_id = self.partner_id.property_account_payable_id

class AccountMove(models.Model):
    _inherit = "account.move"

    of_export = fields.Boolean(string=u'Exporté')

    # Lors d'une saisie d'une pièce comptable, pour préremplir avec la date de la dernière écriture du journal.
    @api.onchange('journal_id')
    def _onchange_journal_id(self):
        if self.journal_id:
            move = self.env['account.move'].search([('journal_id', '=', self.journal_id.id), ('date', '!=', False)], order='date DESC', limit=1)
            if move:
                self.date = move.date

class AccountPayment(models.Model):
    _inherit = "account.payment"

    @api.multi
    def button_invoices(self):
        """ (smart button facture sur les paiements)
        Choisit les vues en fonctions du type de partenaire
        """
        vals = super(AccountPayment, self).button_invoices()
        if (self.partner_type == "customer"):
            vals['views'] = [(self.env.ref('account.invoice_tree').id, 'tree'),
                             (self.env.ref('account.invoice_form').id, 'form')]
        elif (self.partner_type == "supplier"):
            vals['views'] = [(self.env.ref('account.invoice_supplier_tree').id, 'tree'),
                             (self.env.ref('account.invoice_supplier_form').id, 'form')]
        return vals

    def post(self):
        """Lors d'un lettrage d'un paiement, rajoute le libellé sur toutes les écritures du paiement."""
        res = super(AccountPayment, self).post()
        client_line = self.move_line_ids.filtered(lambda line: line.credit > 0)
        if client_line.name == _("Customer Payment"):
            self.move_line_ids.write({"name":((self.partner_id.name or self.partner_id.parent_id.name or '')[:30] + " " + (self.communication or '')).strip()})  # Permet d'avoir toutes les lignes avec le même libellé
        else:
            self.move_line_ids.write({"name": client_line.name})
        return res
