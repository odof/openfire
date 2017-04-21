# -*- coding: utf-8 -*-

from odoo import models, fields, api

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
        self.ensure_one()
        if not taxes:
            taxes = self.default_tax_ids
        return super(AccountFiscalPosition, self).map_tax(taxes, product=product, partner=partner)

class AccountInvoiceLine(models.Model):
    _inherit = 'account.invoice.line'

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
