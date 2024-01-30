# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import fields, models


class OFProductPackLines(models.Model):
    _inherit = 'of.product.pack.lines'

    parent_product_id = fields.Many2one(
        comodel_name='sale.order.line',
        string='Parent Product',
        ondelete='cascade',
        index=True,
        required=True,
    )
    _sql_constraints = [
        (
            'product_uniq',
            'unique(parent_product_id, product_id)',
            "Product must be only once on a pack !",
        ),
    ]

    def _prepare_procurement_values(self, group_id=False):
        """Copy of the original method in sale.order.line to manage pack lines as well"""
        parent_line_procurement_values = self.parent_product_id._prepare_procurement_values(group_id)
        parent_line_procurement_values.update(
            {
                'sale_line_id': self.parent_product_id.id,
            }
        )
        return parent_line_procurement_values
