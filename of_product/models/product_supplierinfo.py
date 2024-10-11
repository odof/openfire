# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class ProductSupplierInfo(models.Model):
    _inherit = "product.supplierinfo"

    of_public_price_untaxed = fields.Float(
        string="Public price excl.",
        default=1.0,
        digits="Product Price",
        required=True,
        help="Public price excluding VAT recommended by the manufacturer",
    )
    pp_currency_id = fields.Many2one(related="currency_id", string="Currency (Public Price)")
    of_discount = fields.Float(string="Discount", digits=(4, 2), compute="_compute_of_discount")
    of_product_category_name = fields.Char(string="Supplier Category")

    # Retrait de la société par défaut
    company_id = fields.Many2one(default=False)

    # On retire ces champs de ceux repris par la duplication
    product_name = fields.Char(copy=False)
    product_code = fields.Char(copy=False)

    @api.depends("of_public_price_untaxed", "price")
    def _compute_of_discount(self):
        for supinfo in self:
            of_public_price_untaxed = supinfo.of_public_price_untaxed
            if supinfo.of_public_price_untaxed != 0:
                supinfo.of_discount = (of_public_price_untaxed - supinfo.price) * 100.00 / of_public_price_untaxed
            else:  # division par 0!
                supinfo.of_discount = -100
