# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class SaleOrder(models.Model):
    _inherit = "sale.order"

    of_product_forbidden_discount = fields.Boolean(string="Discount not allowed for this product")
