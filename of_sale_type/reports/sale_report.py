# -*- coding: utf-8 -*-

from odoo import fields, models


class SaleReport(models.Model):
    _inherit = "sale.report"

    of_sale_type_id = fields.Many2one(comodel_name='of.sale.type', string="Sale order type", readonly=True)

    def _select(self):
        """ Add the sale order type"""
        res = super(SaleReport, self)._select()
        res += ", s.of_sale_type_id AS of_sale_type_id"
        return res

    def _group_by(self):
        """ Add the sale order type"""
        res = super(SaleReport, self)._group_by()
        res += ", s.of_sale_type_id"
        return res
