# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, models


class SaleOrder(models.Model):
    _inherit = "sale.order"

    @api.onchange("sale_order_template_id")
    def _onchange_sale_order_template_id(self):
        super()._onchange_sale_order_template_id()
        for order in self.filtered("sale_order_template_id"):
            order.comment_template_ids = order.sale_order_template_id.of_comment_template_ids
