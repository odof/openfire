# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import UserError,  ValidationError
from odoo.models import regex_order
from odoo.tools.float_utils import float_compare

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

    @api.multi
    @api.constrains('company_id', 'journal_id')
    def _check_journal_company(self):
        """
        Ajout d'une vérification sur la société du journal.
        Si le journal n'est pas de la société de la facture ou une société parente alors renvoi une erreur.
        """
        company_obj = self.env['res.company']
        for invoice in self:
            if invoice.move_name:
                continue
            if invoice.journal_id.company_id not in company_obj.search([('id', 'parent_of', invoice.company_id.id)]):
                raise ValidationError(u'Erreur ! La société du journal est différente de celle de la facture.')

    of_etiquette_partenaire_ids = fields.Many2many('res.partner.category', related='partner_id.category_id', string=u"Étiquettes client")

    of_partner_phone = fields.Char(related='partner_id.phone', string=u"Téléphone du partenaire", readonly=True)
    of_partner_mobile = fields.Char(related='partner_id.mobile', string=u"Mobile du partenaire", readonly=True)
    of_partner_email = fields.Char(related='partner_id.email', string=u"Courriel du partenaire", readonly=True)

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
        self._check_journal_company()  # Ajout de vérification de la société du journal
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

    @api.onchange('company_id')
    def _onchange_company_id(self):
        """
        Recalcul auto du journal par défaut en fonction de la société.
        """
        self.journal_id = self.with_context(company_id=self.company_id.id).default_get(['journal_id'])['journal_id']

class AccountInvoiceLine(models.Model):
    _name = 'account.invoice.line'
    _inherit = ['account.invoice.line', 'of.readgroup']

    of_product_categ_id = fields.Many2one(
        'product.category', related='product_id.categ_id', string=u"Catégorie d'article",
        readonly=True, store=True, index=True
    )
    date_invoice = fields.Date(
        related='invoice_id.date_invoice', string="Date de facturation",
        store=True, index=True
    )
    of_gb_partner_tag_id = fields.Many2one(
        'res.partner.category', compute=lambda *a, **k: {}, search='_search_of_gb_partner_tag_id',
        string="Étiquette client", of_custom_groupby=True)

    of_price_unit_ht = fields.Float(string='Unit Price', compute='_compute_of_price_unit', help="Total amount without taxes", store=True)
    of_price_unit_ttc = fields.Float(string='Unit Price incl', compute='_compute_of_price_unit',
                                     help="Unit price with taxes", store=True)

    price_unit = fields.Float(help="""
    Prix unitaire de l'article.
    À entrer HT ou TTC suivant la TVA de la ligne de facture.
    """)

    @api.depends('price_unit', 'invoice_id.currency_id', 'invoice_id.partner_id', 'product_id',
                 'price_subtotal', 'quantity', 'invoice_line_tax_ids')
    def _compute_of_price_unit(self):
        """
        @ TODO: à fusionner avec _compute_price
        :return:
        """
        for line in self:
            taxes = line.invoice_line_tax_ids.compute_all(line.price_unit, line.invoice_id.currency_id, 1,
                                            product=line.product_id, partner=line.invoice_id.partner_id)
            line.of_price_unit_ht = taxes['total_excluded']
            line.of_price_unit_ttc = taxes['total_included']

    @api.model
    def _search_of_gb_partner_tag_id(self, operator, value):
        return [('partner_id.category_id', operator, value)]

    @api.model
    def _read_group_process_groupby(self, gb, query):
        # Ajout de la possibilité de regrouper par employé
        if gb != 'of_gb_partner_tag_id':
            return super(AccountInvoiceLine, self)._read_group_process_groupby(gb, query)

        alias, _ = query.add_join(
            (self._table, 'res_partner_res_partner_category_rel', 'partner_id', 'partner_id', 'partner_category'),
            implicit=False, outer=True,
        )

        return {
            'field': gb,
            'groupby': gb,
            'type': 'many2one',
            'display_format': None,
            'interval': None,
            'tz_convert': False,
            'qualified_field': '"%s".category_id' % (alias,)
        }

    @api.model
    def of_custom_groupby_generate_order(self, alias, order_field, query, reverse_direction, seen):
        if order_field == 'of_gb_partner_tag_id':
            dest_model = self.env['res.partner.category']
            m2o_order = dest_model._order
            if not regex_order.match(m2o_order):
                # _order is complex, can't use it here, so we default to _rec_name
                m2o_order = dest_model._rec_name

            rel_alias, _ = query.add_join(
                (alias, 'res_partner_res_partner_category_rel', 'partner_id', 'partner_id', 'partner_category_rel'),
                implicit=False, outer=True)
            dest_alias, _ = query.add_join(
                (rel_alias, 'res_partner_category', 'category_id', 'id', 'partner_category'),
                implicit=False, outer=True)
            return dest_model._generate_order_by_inner(dest_alias, m2o_order, query,
                                                       reverse_direction, seen)
        return []

    def _write(self, vals):
        for field in vals:
            if field != 'of_product_categ_id':
                break
        else:
            self = self.sudo()
        return super(AccountInvoiceLine, self)._write(vals)


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

    # Lors d'une saisie d'une pièce comptable, pour préremplir le compte de tiers du partenaire saisi (première ligne uniquement).
    @api.onchange('partner_id')
    def _onchange_partner_id(self):
        if self.partner_id and not self.account_id and not self._context.get('line_ids', False):
            if self.journal_id.type == 'purchase':
                # Pour un journal d'achat on prend le compte de tiers fournisseur.
                self.account_id = self.partner_id.property_account_payable_id
            else:
                # Pour tout autre journal on prend le compte de tiers client.
                self.account_id = self.partner_id.property_account_receivable_id

    @api.multi
    def write(self, vals):
        if 'account_id' in vals:
            for line in self:
                if not line.invoice_id:
                    continue
                invoice = line.invoice_id
                balance = vals.get('debit', line.debit) - vals.get('credit', line.credit)
                if line.invoice_id.type in ('out_invoice', 'in_refund'):
                    balance = -balance

                # On tente de synchroniser le compte utilisé avec la facture
                # 1 - Compte de tiers
                if line.account_id == invoice.account_id:
                    invoice.account_id = vals['account_id']
                    continue

                # 2 - Compte de taxe
                if line.account_id in invoice.tax_line_ids.mapped('account_id'):
                    tax_lines = invoice.tax_line_ids.filtered(lambda l: l.account_id == line.account_id)
                    if tax_lines:
                        if float_compare(sum(tax_lines.mapped('amount')), balance, 2) == 0:
                            tax_lines.write({'account_id': vals['account_id']})
                        else:
                            for tax_line in tax_lines:
                                if float_compare(tax_line.amount, balance, 2) == 0:
                                    tax_line.account_id = vals['account_id']
                                    break
                            else:
                                raise UserError(
                                    u"Vous ne pouvez pas changer le compte \"%s - %s\" car les montants des taxes "
                                    u"de la facture ne correspondent pas." %
                                    (line.account_id.code, line.account_id.name))
                        continue
                    for tax_line in invoice.tax_line_ids:
                        if tax_line.account_id.id == line.account_id.id and float_compare(balance, tax_line.amount, 2) == 0:
                            tax_line.account_id = vals['account_id']
                            break

                # 3 - Compte de ligne de facture
                # On tente de synchroniser le compte utilisé dans les lignes de factures correspondantes

                invoice_lines = invoice.invoice_line_ids.filtered(lambda l: l.account_id.id == self.account_id.id)
                if not invoice_lines:
                    # Les comptes ne sont déjà pas synchronisés, on laisse faire...
                    continue

                # Regroupement des lignes de factures selon la règle définie dans le journal.
                if invoice.journal_id.group_invoice_lines:
                    if invoice.journal_id.group_method == 'product':
                        # Les écritures sont groupées par article
                        values = {}
                        for invoice_line in invoice_lines:
                            product_id = line.product_id.id
                            if product_id in values:
                                vals[product_id] |= invoice_line
                        values = values.values()
                    else:
                        # Les écritures sont groupées par compte
                        values = [invoice_lines]
                else:
                    # Une écriture par ligne de facture
                    values = invoice_lines

                # Les montants des lignes de facture doivent correspondre au montant de l'écriture
                values = [
                    inv_lines for inv_lines in values
                    if float_compare(sum(inv_lines.mapped('price_subtotal')), balance, 2) == 0]
                if not values:
                    raise UserError(
                        u"Vous ne pouvez pas changer le compte \"%s - %s\" car les montants de la facture "
                        u"ne correspondent pas." %
                        (line.account_id.code, line.account_id.name))
                if len(values) > 1:
                    raise UserError(
                        u"Vous ne pouvez pas changer le compte \"%s - %s\" car plusieurs lignes de la facture sont "
                        u"candidates pour ce changement." %
                        (line.account_id.code, line.account_id.name))
                values[0].write({'account_id': vals['account_id']})

        super(AccountMoveLine, self).write(vals)


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

    of_expected_deposit_date = fields.Date(string=u"Date de remise prévue")

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
