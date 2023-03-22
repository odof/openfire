# -*- coding: utf-8 -*-

from odoo import api, fields, models


class SaleReport(models.Model):
    _inherit = 'sale.report'

    of_partner_tags = fields.Char(string=u"Étiquettes du partenaire", readonly=True)
    of_product_tags = fields.Char(string=u"Étiquettes du produit", readonly=True)

    def _select(self):
        res = super(SaleReport, self)._select()
        res += """, (   SELECT  STRING_AGG(RPC.name, ' - ' ORDER BY RPC.name)
                        FROM    res_partner_res_partner_category_rel            RPRPCR
                        ,       res_partner_category                            RPC
                        WHERE   RPRPCR.partner_id                               = partner.id
                        AND     RPC.id                                          = RPRPCR.category_id
                    )  AS of_partner_tags
                    , (   SELECT  STRING_AGG(OPTT.name, ' - ' ORDER BY OPTT.name)
                        FROM    of_product_template_tag_product_template_rel    OPTTPTR
                        ,       of_product_template_tag                         OPTT
                        WHERE   OPTTPTR.product_id                              = t.id
                        AND     OPTT.id                                         = OPTTPTR.tag_id
                    )  AS of_product_tags"""
        return res

    def _group_by(self):
        res = super(SaleReport, self)._group_by()
        res += ", partner.id, t.id"
        return res
