# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class ProductCategory(models.Model):
    _inherit = "product.category"

    of_main_product = fields.Boolean(
        string="Main product",
        help="Items in this category will be considered as main items on customer orders/invoices",
    )
