# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import fields, models


class ProductTemplate(models.Model):
    _inherit = "product.template"

    of_product_type = fields.Selection(string="Product type", related="seller_ids.of_product_type", readonly=False)
