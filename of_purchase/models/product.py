# -*- coding: utf-8 -*-
from odoo import models, fields, api


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    @api.multi
    def _purchase_count(self):
        for template in self:
            template.purchase_count = sum(
                p.purchase_count for p in template.with_context(active_test=False).product_variant_ids)
        return True


class ProductProduct(models.Model):
    _inherit = 'product.product'

    property_of_purchase_coeff = fields.Float(string="Coefficient d'achat", company_dependent=True)

    @api.multi
    def _set_standard_price(self, value):
        super(ProductProduct, self)._set_standard_price(value)
        self.of_purchase_coeff_cost_propagation(value)

    @api.multi
    def of_purchase_coeff_cost_propagation(self, cost):
        # Le coefficient d'achat (property_of_purchase_coeff) est défini sur l'ensemble des sociétés.
        # Si le module of_base_multicompany est installé, il est inutile de le diffuser sur les sociétés "magasins"
        companies = self.env['res.company'].search(['|', ('chart_template_id', '!=', False), ('parent_id', '=', False)])
        property_obj = self.env['ir.property'].sudo()
        coeff_values = {product.id: cost and product.of_seller_price and cost / product.of_seller_price or 1
                        for product in self}
        for company in companies:
            property_obj.with_context(force_company=company.id).set_multi(
                'property_of_purchase_coeff', 'product.product', coeff_values)

    @api.multi
    def of_purchase_coeff_seller_price_propagation(self, seller_price):
        # Le coefficient d'achat (property_of_purchase_coeff) est défini sur l'ensemble des sociétés.
        # Si le module of_base_multicompany est installé, il est inutile de le diffuser sur les sociétés "magasins"
        companies = self.env['res.company'].search(['|', ('chart_template_id', '!=', False), ('parent_id', '=', False)])
        property_obj = self.env['ir.property'].sudo()
        coeff_values = {product.id: product.standard_price and seller_price and product.standard_price / seller_price
                        or 1 for product in self}
        for company in companies:
            property_obj.with_context(force_company=company.id).set_multi(
                'property_of_purchase_coeff', 'product.product', coeff_values)

    @api.multi
    def _purchase_count(self):
        domain = [
            ('product_id', 'in', self.mapped('id')),
        ]
        PurchaseOrderLines = self.env['purchase.order.line'].search(domain)
        for product in self:
            product.purchase_count = len(
                PurchaseOrderLines.filtered(lambda r: r.product_id == product).mapped('order_id'))
