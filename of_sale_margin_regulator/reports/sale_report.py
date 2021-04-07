# -*- coding: utf-8 -*-

from odoo import api, fields, models


class SaleReport(models.Model):
    _inherit = 'sale.report'

    of_presale_margin = fields.Float(string=u"Marge à la confirmation", readonly=True)
    of_sale_price = fields.Float(string=u"CA à la validation", readonly=True)

    def _select(self):
        res = super(SaleReport, self)._select()
        res += """
            , SUM(l.of_presale_margin)  AS of_presale_margin
            , SUM(l.of_sale_price)      AS of_sale_price
        """
        return res
