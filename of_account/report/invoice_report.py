# -*- coding: utf-8 -*-

from odoo import fields, models, api


class AccountInvoiceReport(models.Model):
    _inherit = "account.invoice.report"

    product_qty = fields.Integer()
    price_total = fields.Integer()
    price_average = fields.Integer()
    currency_rate = fields.Integer()
    residual = fields.Integer()
