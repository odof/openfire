# -*- coding: utf-8 -*-

from odoo import models, fields


class AccountInvoiceReport(models.Model):
    _inherit = "account.invoice.report"

    of_sale_type_id = fields.Many2one(comodel_name='of.sale.type', string="Sale order type", readonly=True)

    def _select(self):
        """ Add the sale order type"""
        res = super(AccountInvoiceReport, self)._select()
        res += ", sub.of_sale_type_id AS of_sale_type_id"
        return res

    def _sub_select(self):
        """ Add the sale order type"""
        res = super(AccountInvoiceReport, self)._sub_select()
        res += ", ai.of_sale_type_id AS of_sale_type_id"
        return res

    def _group_by(self):
        """ Add the sale order type"""
        res = super(AccountInvoiceReport, self)._group_by()
        res += ", ai.of_sale_type_id"
        return res
