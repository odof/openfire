# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import fields, models


class ProductSuppliferinfo(models.Model):
    _inherit = "product.supplierinfo"

    of_product_type = fields.Selection(
        selection=[
            ("pellet", "Pellet"),
            ("wood", "Wood"),
            ("gas", "Gas"),
            ("mixed", "Mixed"),
        ],
        string="Type of equipment",
    )
