# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import fields, models


class OFProductPackLines(models.Model):
    _name = 'of.product.pack.lines'
    _description = "Product Pack Lines"
    _rec_name = 'product_id'

    product_id = fields.Many2one(
        comodel_name='product.product',
        string="Product",
        ondelete='cascade',
        index=True,
        required=True,
    )
    quantity = fields.Float(
        required=True,
        default=1.0,
        digits='Product UoS',
    )
