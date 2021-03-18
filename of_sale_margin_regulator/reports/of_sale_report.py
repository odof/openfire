# -*- coding: utf-8 -*-

from odoo import api, fields, models


class SaleReport(models.Model):
    _inherit = 'sale.report'

    of_validated = fields.Boolean(string=u"Devis validé", readonly=True)

    def _select(self):
        res = super(SaleReport, self)._select()
        res += ", s.of_validated as of_validated"
        return res

    def _group_by(self):
        res = super(SaleReport, self)._group_by()
        res += ", s.of_validated"
        return res
