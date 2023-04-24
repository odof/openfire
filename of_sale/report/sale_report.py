# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class SaleReport(models.Model):
    _inherit = 'sale.report'

    of_partner_tags = fields.Char(string="Partner tags", readonly=True)
    of_product_tags = fields.Char(string="Product tags", readonly=True)

    def _select_additional_fields(self):
        res = super()._select_additional_fields()
        res['of_partner_tags'] = (  # nosec B608: we trust env.user.lang
            "(SELECT  STRING_AGG(COALESCE(RPC.name->>'%s', RPC.name->>'en_US'), ' - ' ORDER BY RPC.name) "
            "FROM res_partner_res_partner_category_rel RPRPCR, res_partner_category RPC "
            "WHERE RPRPCR.partner_id = partner.id AND RPC.id = RPRPCR.category_id)"
        ) % self.env.user.lang
        res['of_product_tags'] = (  # nosec B608: we trust env.user.lang
            "(SELECT  STRING_AGG(COALESCE(PTAG.name->>'%s', PTAG.name->>'en_US'), ' - ' ORDER BY PTAG.name) "
            "FROM    product_tag_product_template_rel PTAGPTEMPREL, product_tag PTAG "
            "WHERE   PTAGPTEMPREL.product_template_id = t.id AND PTAG.id = PTAGPTEMPREL.product_tag_id)"
        ) % self.env.user.lang
        return res

    def _group_by_sale(self):
        res = super()._group_by_sale()
        res += ", partner.id, t.id"
        return res
