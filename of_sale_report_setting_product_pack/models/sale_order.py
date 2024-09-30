# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import fields, models


class SaleOrder(models.Model):
    _inherit = "sale.order"

    of_pack_report_type = fields.Selection(
        selection=[
            ("pack_only", "Pack Only"),
            ("pack_components", "Pack and Components"),
            ("pack_components_details", "Pack and Components with prices details"),
        ],
        default="pack_components",
        string="Pack print configuration",
    )

    def _get_order_lines_to_report(self):
        order_lines = super()._get_order_lines_to_report()
        pack_item_lines = self.order_line.filtered(lambda line: line.pack_parent_line_id)
        return order_lines.filtered(lambda line: line not in pack_item_lines)
