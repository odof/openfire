# -*- coding: utf-8 -*-

from odoo import api, fields, models


class SaleReport(models.Model):
    _inherit = "sale.report"

    of_total_price_variation = fields.Float(string=u"Variation de prix totale", readonly=True)

    def _select(self):
        res = super(SaleReport, self)._select()
        res += (",  CASE"
                "       WHEN l.of_is_kit = True AND l.of_pricing = 'computed' THEN"
                "           SUM(OSKL.kit_comp_price_variation * l.product_uom_qty / COALESCE(cr.rate, 1.0))"
                "       ELSE"
                "           SUM(l.of_unit_price_variation * l.product_uom_qty / COALESCE(cr.rate, 1.0))"
                "   END AS of_total_price_variation")
        return res

    def _from(self):
        res = super(SaleReport, self)._from()
        res += """
        LEFT JOIN
        (   SELECT  OSKL.kit_id
            ,       SUM(OSKL.of_unit_price_variation * OSKL.qty_per_kit)    AS kit_comp_price_variation
            FROM    of_saleorder_kit_line                                   OSKL
            GROUP BY OSKL.kit_id
        ) AS OSKL
            ON OSKL.kit_id = l.kit_id
        """
        return res

    def _group_by(self):
        res = super(SaleReport, self)._group_by()
        res += ", l.of_is_kit, l.of_pricing"
        return res
