# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class SaleOrder(models.Model):
    _inherit = "sale.order"

    of_display_reset_option = fields.Boolean(
        string="Display Reset Option Column", compute="_compute_of_display_reset_option", help="For UX Purpose"
    )

    @api.depends("order_line", "order_line.product_template_id")
    def _compute_of_display_reset_option(self):
        for order in self:
            order.of_display_reset_option = any(line.of_order_line_option_id for line in order.order_line)
