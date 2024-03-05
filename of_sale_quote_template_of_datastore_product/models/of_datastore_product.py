# -*- coding: utf-8 -*-

from odoo import models, fields, api, registry, _


class SaleQuoteLine(models.Model):
    _name = 'sale.quote.line'
    _inherit = ['sale.quote.line', 'of.datastore.product.reference']


class OfSaleQuoteTemplateLayoutCategory(models.Model):
    _name = 'of.sale.quote.template.layout.category'
    _inherit = ['of.sale.quote.template.layout.category', 'of.datastore.product.reference']
