# -*- coding: utf-8 -*-

from odoo import api, models, fields
from odoo.exceptions import UserError

"""
Modification OpenFire du comportement des factures d'acompte.
Le wizard ne génère plus automatiquement d'article.
Le wizard permet le choix d'un article parmi ceux présents dans la catégorie des articles d'acompte.
"""
class SaleAdvancePaymentInv(models.TransientModel):
    _inherit = "sale.advance.payment.inv"

    @api.model
    def _default_product_categ_id(self):
        categ_id = self.env['ir.values'].get_default('sale.config.settings', 'of_deposit_product_categ_id_setting')
        return self.env['product.category'].browse(categ_id)

    @api.model
    def _default_product_id(self):
        categ = self._default_product_categ_id()
        products = categ and self.env['product.product'].search([('categ_id', '=', categ.id)])
        return len(products) == 1 and products or self.env['product.product'].browse()

    product_categ_id = fields.Many2one(
        'product.category', string=u"Catégorie des articles d'acompte",
        default=lambda self: self._default_product_categ_id())

    product_id = fields.Many2one(
        domain="[('type', '=', 'service'), ('categ_id', '=', product_categ_id)]",
        default=lambda self: self._default_product_id())
    of_nb_products = fields.Integer(compute="_compute_of_nb_products")

    @api.depends('product_categ_id')
    def _compute_of_nb_products(self):
        categ = self._default_product_categ_id()
        nb_products = categ and self.env['product.product'].search([('categ_id', '=', categ.id)], count=True) or 0
        self.update({'of_nb_products': nb_products})

    @api.multi
    def _create_invoice(self, order, so_line, amount):
        invoice = super(SaleAdvancePaymentInv, self)._create_invoice(order, so_line, amount)
        # La méthode _onchange_tax est définie dans le module of_account_tax et recalcule le compte comptable de
        # la ligne de facture en fonction de ses taxes.
        invoice.invoice_line_ids.onchange_tax_ids()
        return invoice

    @api.multi
    def create_invoices(self):
        if self.advance_payment_method in ('percentage', 'fixed') and not self.product_id:
            raise UserError(u"Vous devez sélectionner un article d'acompte")
        if self.advance_payment_method == 'percentage':
            # Le pourcentage doit s'appliquer sur le TTC et non sur le HT
            amount = self.amount
            sale_orders = self.env['sale.order'].browse(self._context.get('active_ids', []))
            for order in sale_orders:
                self.amount = amount * order.amount_total / order.amount_untaxed
                result = super(SaleAdvancePaymentInv, self.with_context(active_ids=order.ids)).create_invoices()
            if len(sale_orders) > 1 and self._context.get('open_invoices', False):
                result = sale_orders.action_view_invoice()
        else:
            result = super(SaleAdvancePaymentInv, self).create_invoices()
        return result
