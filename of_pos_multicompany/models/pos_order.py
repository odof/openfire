# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class PosOrder(models.Model):
    _inherit = 'pos.order'

    @api.model
    def _amount_line_tax(self, line, fiscal_position_id):
        # OF - Modification OpenFire
        taxes = line.tax_ids.filtered(
            lambda t: t.company_id.id in (line.order_id.company_id.id,
                                          line.order_id.company_id.accounting_company_id.id))
        # OF - Fin Modification OpenFire
        if fiscal_position_id:
            taxes = fiscal_position_id.map_tax(taxes, line.product_id, line.order_id.partner_id)
        price = line.price_unit * (1 - (line.discount or 0.0) / 100.0)
        taxes = taxes.compute_all(price, line.order_id.pricelist_id.currency_id, line.qty, product=line.product_id,
                                  partner=line.order_id.partner_id or False)['taxes']
        return sum(tax.get('amount', 0.0) for tax in taxes)

    def _action_create_invoice_line(self, line=False, invoice_id=False):
        InvoiceLine = self.env['account.invoice.line']
        inv_name = line.product_id.name_get()[0][1]
        inv_line = {
            'invoice_id': invoice_id,
            'product_id': line.product_id.id,
            'quantity': line.qty,
            'account_analytic_id': self._prepare_analytic_account(line),
            'name': inv_name,
        }
        # Oldlin trick
        invoice_line = InvoiceLine.sudo().new(inv_line)
        invoice_line._onchange_product_id()
        # OF - Modification OpenFire
        invoice_line.invoice_line_tax_ids = invoice_line.invoice_line_tax_ids.filtered(
            lambda t: t.company_id.id in (line.order_id.company_id.id,
                                          line.order_id.company_id.accounting_company_id.id)).ids
        # OF - Fin Modification OpenFire
        fiscal_position_id = line.order_id.fiscal_position_id
        if fiscal_position_id:
            invoice_line.invoice_line_tax_ids = fiscal_position_id.map_tax(
                invoice_line.invoice_line_tax_ids, line.product_id, line.order_id.partner_id)
        invoice_line.invoice_line_tax_ids = invoice_line.invoice_line_tax_ids.ids
        # We convert a new id object back to a dictionary to write to
        # bridge between old and new api
        inv_line = invoice_line._convert_to_write({name: invoice_line[name] for name in invoice_line._cache})
        inv_line.update(price_unit=line.price_unit, discount=line.discount)
        return InvoiceLine.sudo().create(inv_line)


class PosOrderLine(models.Model):
    _inherit = 'pos.order.line'

    @api.onchange('product_id')
    def _onchange_product_id(self):
        if self.product_id:
            if not self.order_id.pricelist_id:
                raise UserError(
                    _('You have to select a pricelist in the sale form !\n'
                      'Please set one before choosing a product.'))
            price = self.order_id.pricelist_id.get_product_price(
                self.product_id, self.qty or 1.0, self.order_id.partner_id)
            self._onchange_qty()
            # OF - Modification OpenFire
            self.tax_ids = self.product_id.taxes_id.filtered(
                lambda r: not self.company_id or r.company_id in (self.company_id,
                                                                  self.company_id.accounting_company_id))
            # OF - Fin Modification OpenFire
            fpos = self.order_id.fiscal_position_id
            tax_ids_after_fiscal_position = fpos.map_tax(self.tax_ids, self.product_id,
                                                         self.order_id.partner_id) if fpos else self.tax_ids
            self.price_unit = self.env['account.tax']._fix_tax_included_price_company(
                price, self.product_id.taxes_id, tax_ids_after_fiscal_position, self.company_id)
