# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError, RedirectWarning
from odoo.models import regex_order
from odoo.addons.account.models.account_invoice import AccountInvoice
from odoo.tools.float_utils import float_compare

NEGATIVE_TERM_OPERATORS = ('!=', 'not like', 'not ilike', 'not in')


@api.onchange('partner_id', 'company_id')
def _onchange_partner_id(self):
    u"""OpenFire edit : split this function in 2 to isolate the warning part and allow inheritance"""
    account_id = False
    payment_term_id = False
    fiscal_position = False
    company_id = self.company_id.id
    p = self.partner_id if not company_id else self.partner_id.with_context(force_company=company_id)
    res = {}
    type = self.type
    if p:
        rec_account = p.property_account_receivable_id
        pay_account = p.property_account_payable_id
        if not rec_account and not pay_account:
            action = self.env.ref('account.action_account_config')
            msg = _('Cannot find a chart of accounts for this company, You should configure it. \n'
                    'Please go to Account Configuration.')
            raise RedirectWarning(msg, action.id, _('Go to the configuration panel'))

        if type in ('in_invoice', 'in_refund'):
            account_id = pay_account.id
            payment_term_id = p.property_supplier_payment_term_id.id
        else:
            account_id = rec_account.id
            payment_term_id = p.property_payment_term_id.id

        delivery_partner_id = self.get_delivery_partner_id()
        fiscal_position = self.env['account.fiscal.position'].get_fiscal_position(
            self.partner_id.id, delivery_id=delivery_partner_id)

    # OpenFire edit : old block was here

    self.account_id = account_id
    self.payment_term_id = payment_term_id
    self.date_due = False
    self.fiscal_position_id = fiscal_position

    if type in ('in_invoice', 'out_refund'):
        bank_ids = p.commercial_partner_id.bank_ids
        bank_id = bank_ids[0].id if bank_ids else False
        self.partner_bank_id = bank_id
        res['domain'] = {'partner_bank_id': [('id', 'in', bank_ids.ids)]}

    return res


@api.onchange('partner_id')
def _onchange_partner_id_warning(self):
    u"""OpenFire Made from the splitting of _onchange_partner_id to allow inheritance"""
    res = {}
    p = self.partner_id
    if p:
        # If partner has no warning, check its company
        if p.invoice_warn == 'no-message' and p.parent_id:
            p = p.parent_id
        if p.invoice_warn != 'no-message':
            # Block if partner only has warning but parent company is blocked
            if p.invoice_warn != 'block' and p.parent_id and p.parent_id.invoice_warn == 'block':
                p = p.parent_id
            warning = {
                'title': _("Warning for %s") % p.name,
                'message': p.invoice_warn_msg
            }
            res['warning'] = warning
            if p.invoice_warn == 'block':
                self.partner_id = False
    return res


@api.multi
def get_taxes_values(self):
    """OpenFire : fix wrong taxes calculation with global rounding when using included taxes"""
    tax_grouped = {}
    round_curr = self.currency_id.round
    for line in self.invoice_line_ids:
        price_unit = line.price_unit * (1 - (line.discount or 0.0) / 100.0)
        taxes = line.invoice_line_tax_ids.compute_all(price_unit, self.currency_id, line.quantity, line.product_id, self.partner_id)['taxes']
        for tax in taxes:
            val = self._prepare_tax_line_vals(line, tax)
            key = self.env['account.tax'].browse(tax['id']).get_grouping_key(val)

            # Modification OF : Ce qu'on retire au HT, on l'ajoute à la taxe
            val['amount'] += val['base'] - round_curr(val['base'])
            # Fin de modification
            if key not in tax_grouped:
                tax_grouped[key] = val
                tax_grouped[key]['base'] = round_curr(val['base'])
            else:
                tax_grouped[key]['amount'] += val['amount']
                tax_grouped[key]['base'] += round_curr(val['base'])
    return tax_grouped


AccountInvoice._onchange_partner_id = _onchange_partner_id
AccountInvoice._onchange_partner_id_warning = _onchange_partner_id_warning
AccountInvoice.get_taxes_values = get_taxes_values


class AccountAccount(models.Model):
    _inherit = 'account.account'

    of_account_counterpart_id = fields.Many2one('account.account', string="Compte de contrepartie")

    @api.model
    def create(self, vals):
        if 'group_id' in self._fields and '' not in vals:
            # Le module OCA des groupes de comptes est installé et le groupe n'est pas mentionné.
            # (module : account-financial-tools/account_group)
            # On cherche le groupe adapté en fonction du préfixe.
            # Code copié de la fonction account.account.onchange_code() du module account_group.

            group_obj = self.env['account.group']
            group = False
            code_prefix = vals.get('code', '')
            # find group with longest matching prefix
            while code_prefix:
                matching_group = group_obj.search([('code_prefix', '=', code_prefix)], limit=1)
                if matching_group:
                    group = matching_group.id
                    break
                code_prefix = code_prefix[:-1]
            vals['group_id'] = group
        return super(AccountAccount, self).create(vals)


class AccountConfigSettings(models.TransientModel):
    _inherit = 'account.config.settings'

    # Paramètre de la date d'échéance des factures
    of_date_due = fields.Selection(
        [(0, u"Date d'échéance en fonction des conditions de règlement"),
         (1, u"Modification manuelle de la date d'échéance possible "
             u"(non recalcul suivant conditions de règlement si date déjà renseignée)")],
        string=u"(OF) Date d'échéance")

    @api.multi
    def set_of_date_due_defaults(self):
        return self.env['ir.values'].sudo().set_default('account.config.settings', 'of_date_due', self.of_date_due)


class AccountInvoice(models.Model):
    _inherit = 'account.invoice'

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

    of_etiquette_partenaire_ids = fields.Many2many(
        'res.partner.category', related='partner_id.category_id', string=u"Étiquettes client")

    of_partner_phone = fields.Char(related='partner_id.phone', string=u"Téléphone du partenaire", readonly=True)
    of_partner_mobile = fields.Char(related='partner_id.mobile', string=u"Mobile du partenaire", readonly=True)
    of_partner_email = fields.Char(related='partner_id.email', string=u"Courriel du partenaire", readonly=True)

    @api.onchange('partner_id')
    def _onchange_partner_id_warning(self):
        partner = self.partner_id

        # If partner has no warning, check its parents
        # invoice_warn is shared between different objects
        if not partner.of_is_account_warn and partner.parent_id:
            partner = partner.parent_id

        if partner.of_is_account_warn and partner.invoice_warn != 'no-message':
            return super(AccountInvoice, self)._onchange_partner_id_warning()
        return

    # Date d'échéance des factures
    # Surcharge de la méthode pour permettre la comparaison avec le paramètrage du mode de calcul
    # de la date d'échéance (manuel/auto).
    @api.onchange('payment_term_id', 'date_invoice')
    def _onchange_payment_term_date_invoice(self):
        param_date_due = self.env['ir.values'].get_default('account.config.settings', 'of_date_due')
        date_invoice = self.date_invoice
        if not date_invoice:
            date_invoice = fields.Date.context_today(self)
        if not self.payment_term_id:
            # Quand pas de condition de règlement définie
            if (param_date_due and not self.date_due) or not param_date_due:
                # On rajoute la vérification pour permettre de modifier manuellement la date d'échéance.
                self.date_due = self.date_due or self.date_invoice
        else:
            pterm = self.payment_term_id
            pterm_list = pterm.with_context(currency_id=self.company_id.currency_id.id)\
                              .compute(value=1, date_ref=date_invoice)[0]
            if (param_date_due and not self.date_due) or not param_date_due:
                # On rajoute la vérification pour permettre de modifier manuellement la date d'échéance.
                self.date_due = max(line[0] for line in pterm_list)

    @api.multi
    def action_invoice_open(self):
        """Mettre le libellé des écritures comptables d'une facture avec nom client (30 1er caractères) + no facture"""
        self._check_journal_company()  # Ajout de vérification de la société du journal
        res = super(AccountInvoice, self).action_invoice_open()
        for invoice in self:
            ref = ((invoice.partner_id.name or invoice.partner_id.parent_id.name or '')[:30]
                   + ' ' + invoice.number).strip()
            if invoice.type in ('in_invoice', 'in_refund'):
                # Facture fournisseur
                ref = (ref + ' ' + (invoice.reference or '')).rstrip()
            invoice.move_id.line_ids.write({'name': ref})
            invoice.move_id.write({'ref': ref})
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

    of_product_default_code = fields.Char(related='product_id.default_code', string=u"Référence article", readonly=True)
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
        string=u"Étiquette client", of_custom_groupby=True)

    of_price_unit_ht = fields.Float(
        string='Unit Price', compute='_compute_of_price_unit', help="Total amount without taxes", store=True)
    of_price_unit_ttc = fields.Float(
        string='Unit Price incl', compute='_compute_of_price_unit', help="Unit price with taxes", store=True)

    price_unit = fields.Float(
        help=u"""
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
            taxes = line.invoice_line_tax_ids.compute_all(
                line.price_unit, line.invoice_id.currency_id, 1,
                product=line.product_id,
                partner=line.invoice_id.partner_id)
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


class AccountMove(models.Model):
    _inherit = 'account.move'

    of_export = fields.Boolean(string=u"Exporté")

    # Lors d'une saisie d'une pièce comptable, pour préremplir avec la date de la dernière écriture du journal.
    @api.onchange('journal_id')
    def _onchange_journal_id(self):
        if self.journal_id:
            move = self.env['account.move'].search(
                [('journal_id', '=', self.journal_id.id), ('date', '!=', False)],
                order='date DESC', limit=1)
            if move:
                self.date = move.date


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    @api.model
    def get_journal_types(self):
        return self.env['account.journal'].fields_get(['type'], ['selection'])['type']['selection']

    of_journal_type = fields.Selection(
        selection=lambda s: s.get_journal_types(), related='move_id.journal_id.type', string="Type de journal",
        readonly=True)

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

        lines = self.env['account.move'].resolve_2many_commands(
            'line_ids', lines, ('account_id', 'debit', 'credit', 'date_maturity'))
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
        """Mettre le libellé des écritures comptables d'un paiement avec nom client (30 1ers caractères) + no facture"""
        res = super(AccountMoveLine, self).reconcile(
            writeoff_acc_id=writeoff_acc_id, writeoff_journal_id=writeoff_journal_id)
        move_lines = self.filtered(
            lambda l: (l.reconciled or len(l.matched_debit_ids) == 1) and l.payment_id and l.account_id.reconcile)
        for line in move_lines:
            debit_lines = line.matched_debit_ids.mapped('debit_move_id')
            invoices = debit_lines.mapped('invoice_id')
            if len(invoices) == 1:
                name_infos = [(invoices.partner_id.name or invoices.partner_id.parent_id.name or '')[:30],
                              invoices.number]
                name = ' '.join([text for text in name_infos if text])
                line.move_id.line_ids.with_context(check_move_validity=False).write({'name': name})
                try:
                    line.move_id.write({'ref': name})
                except UserError:
                    # Avec le module OCA des verrouillages d'écritures, le write peut générer une erreur
                    # Il ne faut pas qu'elle soit bloquante pour les lettrages
                    pass
        return res

    # Lors d'une saisie d'une pièce comptable, pour préremplir le compte de tiers du partenaire saisi
    # (première ligne uniquement).
    @api.onchange('partner_id')
    def _onchange_partner_id(self):
        if self.partner_id and not self.account_id and not self._context.get('line_ids', False):
            if self.journal_id.type == 'purchase'\
                    or (self.journal_id.type != 'sale' and self.partner_id.supplier and not self.partner_id.customer):
                # Pour un journal d'achat on prend le compte de tiers fournisseur.
                # Pour un journal qui n'est pas d'achat, on prend le compte de tiers fournisseur si le partenaire
                #   est un fournisseur et n'est pas un client.
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
                        if tax_line.account_id.id == line.account_id.id\
                                and float_compare(balance, tax_line.amount, 2) == 0:
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

        return super(AccountMoveLine, self).write(vals)
