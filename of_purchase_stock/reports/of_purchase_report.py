# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class PurchaseReport(models.Model):
    _inherit = "purchase.report"

    of_brand_id = fields.Many2one(comodel_name="of.product.brand", string="Brand", readonly=True)

    def _select(self):
        select_str = super()._select()
        select_str += """
            , t.brand_id AS of_brand_id
            """
        return select_str

    def _group_by(self):
        group_by_str = super()._group_by()
        group_by_str += """,
            t.brand_id"""
        return group_by_str
