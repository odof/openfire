# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import UserError

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
