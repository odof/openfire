# -*- coding: utf-8 -*-

from odoo import models, fields, api

class AccountConfigSettings(models.TransientModel):
    _inherit = 'account.config.settings'

    of_default_sale_tax_service_id = fields.Many2one('account.tax', string="Taxe de vente par défaut (service)")
    of_default_purchase_tax_service_id = fields.Many2one('account.tax', string="Taxe d'achat par défaut (service)")

    @api.multi
    def set_of_default_sale_tax_service_id(self):
        return self.env['ir.values'].sudo().set_default('account.config.settings', 'of_default_sale_tax_service_id', self.of_default_sale_tax_service_id.id, company_id=self.company_id.id)

    @api.multi
    def set_of_default_purchase_tax_service_id(self):
        return self.env['ir.values'].sudo().set_default('account.config.settings', 'of_default_purchase_tax_service_id', self.of_default_purchase_tax_service_id.id, company_id=self.company_id.id)

    @api.onchange('company_id')
    def onchange_company_id(self):
        super(AccountConfigSettings, self).onchange_company_id()
        if self.company_id:
            # Mise à jour des taxes par défaut des services
            ir_values = self.env['ir.values']
            taxes_id = ir_values.get_default('account.config.settings', 'of_default_sale_tax_service_id', company_id=self.company_id.id)
            supplier_taxes_id = ir_values.get_default('account.config.settings', 'of_default_purchase_tax_service_id', company_id=self.company_id.id)
            self.of_default_sale_tax_service_id = isinstance(taxes_id, list) and len(taxes_id) > 0 and taxes_id[0] or taxes_id
            self.of_default_purchase_tax_service_id = isinstance(supplier_taxes_id, list) and len(supplier_taxes_id) > 0 and supplier_taxes_id[0] or supplier_taxes_id
        return {}

class ProductTemplate(models.Model):
    _inherit = "product.template"

    @api.onchange('type')
    def onchange_type(self):
        """ Change les taxes de vente et d'achat en fonction du type d'article """
        ir_values_obj = self.env['ir.values']
        user_company = self.env.user.company_id
        sale_taxes_id = ir_values_obj.get_default('product.template', 'taxes_id', company_id=user_company.id)
        supplier_taxes_id = ir_values_obj.get_default('product.template', 'supplier_taxes_id', company_id=user_company.id)
        if self.type == 'service':
            service_sale_tax = ir_values_obj.get_default('account.config.settings', 'of_default_sale_tax_service_id', company_id=user_company.id)
            service_purchase_tax = ir_values_obj.get_default('account.config.settings', 'of_default_purchase_tax_service_id', company_id=user_company.id)
            sale_taxes_id = service_sale_tax and [service_sale_tax] or sale_taxes_id
            supplier_taxes_id = service_purchase_tax and [service_purchase_tax] or supplier_taxes_id
        self.taxes_id = [(4, sale_tax_id) for sale_tax_id in sale_taxes_id] if sale_taxes_id else []
        self.supplier_taxes_id = [(4, supplier_tax_id) for supplier_tax_id in supplier_taxes_id] if supplier_taxes_id else []
