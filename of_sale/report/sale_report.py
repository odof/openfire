# -*- coding: utf-8 -*-

from odoo import api, fields, models


class SaleReport(models.Model):
    _inherit = 'sale.report'

    of_partner_tags = fields.Char(string=u"Étiquettes du partenaire", readonly=True)

    def _select(self):
        res = super(SaleReport, self)._select()
        res += """, (   SELECT  STRING_AGG(RPC.name, ' - ' ORDER BY RPC.name)
                        FROM    res_partner_res_partner_category_rel            RPRPCR
                        ,       res_partner_category                            RPC
                        WHERE   RPRPCR.partner_id                               = partner.id
                        AND     RPC.id                                          = RPRPCR.category_id
                    )  AS of_partner_tags"""
        return res

    def _group_by(self):
        res = super(SaleReport, self)._group_by()
        res += ", partner.id"
        return res
