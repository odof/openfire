# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import UserError
from odoo.addons.account.models.chart_template import AccountChartTemplate


@api.multi
def _load_template(self, company, code_digits=None, transfer_account_id=None, account_ref=None, taxes_ref=None):
    """ Generate all the objects from the templates

        :param company: company the wizard is running for
        :param code_digits: number of digits the accounts code should have in the COA
        :param transfer_account_id: reference to the account template that will be used as intermediary account for transfers between 2 liquidity accounts
        :param acc_ref: Mapping between ids of account templates and real accounts created from them
        :param taxes_ref: Mapping between ids of tax templates and real taxes created from them
        :returns: tuple with a dictionary containing
            * the mapping between the account template ids and the ids of the real accounts that have been generated
              from them, as first item,
            * a similar dictionary for mapping the tax templates and taxes, as second item,
        :rtype: tuple(dict, dict, dict)
    """
    self.ensure_one()
    if account_ref is None:
        account_ref = {}
    if taxes_ref is None:
        taxes_ref = {}
    if not code_digits:
        code_digits = self.code_digits
    if not transfer_account_id:
        transfer_account_id = self.transfer_account_id
    AccountTaxObj = self.env['account.tax']

    # Generate taxes from templates.
    generated_tax_res = self.tax_template_ids._generate_tax(company)
    taxes_ref.update(generated_tax_res['tax_template_to_tax'])

    # Generating Accounts from templates.
    account_template_ref = self.generate_account(taxes_ref, account_ref, code_digits, company)
    account_ref.update(account_template_ref)

    # writing tax values after creation of taxes and accounts
    for key, value in taxes_ref.items():
        tax_tmpl = self.env['account.tax.template'].browse(key)
        if tax_tmpl.account_ids:
            self.env['account.tax'].browse(value).write({
                'account_ids': [(0, 0, dict({'account_src_id': account_template_ref[t.account_src_id.id],
                                             'account_dest_id': account_template_ref[t.account_dest_id.id]}))
                                for t in tax_tmpl.account_ids]
            })

    # writing account values after creation of accounts
    company.transfer_account_id = account_template_ref[transfer_account_id.id]
    for key, value in generated_tax_res['account_dict'].items():
        if value['refund_account_id'] or value['account_id']:
            AccountTaxObj.browse(key).write({
                'refund_account_id': account_ref.get(value['refund_account_id'], False),
                'account_id': account_ref.get(value['account_id'], False),
            })

    # Create Journals - Only done for root chart template
    if not self.parent_id:
        self.generate_journals(account_ref, company)

    # generate properties function
    self.generate_properties(account_ref, company)

    # Generate Fiscal Position , Fiscal Position Accounts and Fiscal Position Taxes from templates
    self.generate_fiscal_position(taxes_ref, account_ref, company)

    # Generate account operation template templates
    self.generate_account_reconcile_model(taxes_ref, account_ref, company)

    return account_ref, taxes_ref


@api.multi
def generate_fiscal_position(self, tax_template_ref, acc_template_ref, company):
    """ This method generate Fiscal Position, Fiscal Position Accounts and Fiscal Position Taxes from templates.

        :param chart_temp_id: Chart Template Id.
        :param taxes_ids: Taxes templates reference for generating account.fiscal.position.tax.
        :param acc_template_ref: Account templates reference for generating account.fiscal.position.account.
        :param company_id: company_id selected from wizard.multi.charts.accounts.
        :returns: True
    """
    self.ensure_one()
    positions = self.env['account.fiscal.position.template'].search([('chart_template_id', '=', self.id)])
    for position in positions:
        new_fp = self.create_record_with_xmlid(
            company, position, 'account.fiscal.position',
            {'company_id': company.id,
             'name': position.name,
             'note': position.note,
             'default_tax_ids': [(6, 0, [tax_template_ref[t.id] for t in position.default_tax_ids])]})
        for tax in position.tax_ids:
            self.create_record_with_xmlid(company, tax, 'account.fiscal.position.tax', {
                'tax_src_id': tax_template_ref[tax.tax_src_id.id],
                'tax_dest_id': tax.tax_dest_id and tax_template_ref[tax.tax_dest_id.id] or False,
                'position_id': new_fp
            })
        for acc in position.account_ids:
            self.create_record_with_xmlid(company, acc, 'account.fiscal.position.account', {
                'account_src_id': acc_template_ref[acc.account_src_id.id],
                'account_dest_id': acc_template_ref[acc.account_dest_id.id],
                'position_id': new_fp
            })
    return True


AccountChartTemplate._load_template = _load_template
AccountChartTemplate.generate_fiscal_position = generate_fiscal_position


class AccountTax(models.Model):
    _inherit = 'account.tax'

    account_ids = fields.One2many('of.account.tax.account', 'tax_id', string='Correspondance de comptes', copy=True)

    @api.multi
    def map_account(self, account):
        self.ensure_one()
        for pos in self.account_ids:
            if pos.account_src_id == account:
                return pos.account_dest_id
        return account

# Copié depuis la classe account.fiscal.position.account
class OfAccountTaxAccount(models.Model):
    _name = 'of.account.tax.account'
    _description = 'Comptes des taxes'
    _rec_name = 'tax_id'

    tax_id = fields.Many2one('account.tax', string='Taxe', required=True, ondelete='cascade')
    account_src_id = fields.Many2one('account.account', string="Compte de l'article",
                                     domain=[('deprecated', '=', False)], required=True)
    account_dest_id = fields.Many2one('account.account', string=u"Compte à utiliser à la place",
                                      domain=[('deprecated', '=', False)], required=True)

    _sql_constraints = [
        ('of_account_src_dest_uniq',
         'unique (tax_id,account_src_id,account_dest_id)',
         'Vous ne pouvez créer deux correspondances de comptes identiques sur une même taxe.')
    ]

class AccountFiscalPosition(models.Model):
    _inherit = 'account.fiscal.position'

    default_tax_ids = fields.Many2many('account.tax', string=u"Taxes par défaut",
                                       help=u"Taxes utilisées quand aucun compte de taxes n'est défini dans l'article")

    @api.multi
    def map_tax(self, taxes, product=None, partner=None):
        if not self:
            if self._context.get('website_id'):
                return taxes
            raise UserError(u"Veuillez renseigner une position fiscale")
        self.ensure_one()
        if not taxes:
            taxes = self.default_tax_ids
        return super(AccountFiscalPosition, self).map_tax(taxes, product=product, partner=partner)

    @api.model
    def _get_fpos_by_region(self, country_id=False, state_id=False, zipcode=False, vat_required=False):
        # Dans le cas où un client n'a pas de pays, on veut quand-même récupérer une position fiscale par défaut
        if country_id:
            return super(AccountFiscalPosition, self)._get_fpos_by_region(country_id=country_id, state_id=state_id, zipcode=zipcode, vat_required=vat_required)

        base_domain = [('auto_apply', '=', True), ('vat_required', '=', vat_required)]
        if self.env.context.get('force_company'):
            base_domain.append(('company_id', '=', self.env.context.get('force_company')))
        null_country_dom = [('country_id', '=', False), ('country_group_id', '=', False)]

        fpos = self.search(base_domain + null_country_dom, limit=1)
        return fpos or False


class OfAccountTaxAccountTemplate(models.Model):
    _name = 'of.account.tax.account.template'
    _description = 'Modèle de comptes de taxes'
    _rec_name = 'template_tax_id'

    template_tax_id = fields.Many2one(
        'account.tax.template', string='Modèle de taxe', required=True, ondelete='cascade')
    account_src_id = fields.Many2one(
        'account.account.template', string="Compte de l'article", domain=[('deprecated', '=', False)], required=True)
    account_dest_id = fields.Many2one(
        'account.account.template', string=u"Compte à utiliser à la place", domain=[('deprecated', '=', False)],
        required=True)

    _sql_constraints = [
        ('of_account_src_dest_uniq',
         'unique (template_tax_id, account_src_id, account_dest_id)',
         'Vous ne pouvez créer deux correspondances de comptes identiques sur une même taxe.')
    ]


class AccountTaxTemplate(models.Model):
    _inherit = 'account.tax.template'

    account_ids = fields.One2many(
        'of.account.tax.account.template', 'template_tax_id', string='Correspondance de comptes')


class AccountFiscalPositionTemplate(models.Model):
    _inherit = 'account.fiscal.position.template'

    default_tax_ids = fields.Many2many('account.tax.template')


class AccountInvoiceLine(models.Model):
    _inherit = 'account.invoice.line'

    @api.onchange('product_id')
    def _onchange_product_id(self):
        taxes = self.invoice_line_tax_ids
        res = super(AccountInvoiceLine, self)._onchange_product_id()
        if self._context.get('of_force_product_onchange_tax') or self.invoice_line_tax_ids == taxes:
            # Odoo recalcule le compte comptable en fonction de la position fiscale et du nouvel article sélectionné
            # On doit donc s'assurer de ré-appliquer les règles OpenFire de la taxe
            self.onchange_tax_ids()
        return res

    @api.onchange('invoice_line_tax_ids')
    def onchange_tax_ids(self):
        # Recalcul du compte comptable en fonction des taxes sélectionnées
        account = self.account_id
        if self.product_id:
            account = self.get_invoice_line_account(self.invoice_id.type, self.product_id, self.invoice_id.fiscal_position_id, self.invoice_id.company_id)
        for tax in self.invoice_line_tax_ids:
            account = tax.map_account(account)
        if self.account_id != account:
            self.account_id = account

class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    @api.multi
    def _prepare_invoice_line(self, qty):
        res = super(SaleOrderLine, self)._prepare_invoice_line(qty)

        account = self.env['account.account'].browse(res['account_id'])
        for tax in self.tax_id:
            account = tax.map_account(account)
        res['account_id'] = account.id
        return res

class AccountInvoice(models.Model):
    _inherit = "account.invoice"

    def _prepare_invoice_line_from_po_line(self, line):
        invoice_line_obj = self.env['account.invoice.line']
        tax_obj = self.env['account.tax']
        data = super(AccountInvoice, self)._prepare_invoice_line_from_po_line(line)

        account = invoice_line_obj.get_invoice_line_account(self.type, line.product_id, line.order_id.fiscal_position_id, self.company_id)
        if data['invoice_line_tax_ids']:
            tax_ids = tax_obj.browse(data['invoice_line_tax_ids'])
            for tax in tax_ids:
                account = tax.map_account(account)

        if account:
            data['account_id'] = account.id
        return data
