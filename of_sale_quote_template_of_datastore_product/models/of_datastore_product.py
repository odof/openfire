# -*- coding: utf-8 -*-

from odoo import models, fields, api, registry, _


class SaleQuoteLine(models.Model):
    _name = 'sale.quote.line'
    _inherit = ['sale.quote.line', 'of.datastore.product.reference']


class OfSaleQuoteTemplateLayoutCategory(models.Model):
    _name = 'of.sale.quote.template.layout.category'
    _inherit = ['of.sale.quote.template.layout.category', 'of.datastore.product.reference']


class OfSelectProductWizard(models.TransientModel):
    _name = 'of.select.product.wizard'
    _inherit = ['of.select.product.wizard', 'of.datastore.product.reference']


class OfSelectOrderProductWizard(models.TransientModel):
    _name = 'of.select.order.product.wizard'
    _inherit = ['of.select.order.product.wizard', 'of.datastore.product.reference']
