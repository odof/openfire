# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import _, api, fields, models
from odoo.exceptions import UserError


class PricelistItem(models.Model):
    _inherit = "product.pricelist.item"

    percent_price = fields.Float(
        string="Percentage Price", compute="_compute_percent_price", readonly=False, store=True
    )
    of_percent_price_formula = fields.Char(
        string="Percentage (discount)", help='Discount or amount of discounts.\nEg. "40 + 10.5" equals "46.3"'
    )
    of_brand_ids = fields.Many2many(
        comodel_name="of.product.brand",
        string="Marques",
        help="Si renseigné, la règle s'appliquera uniquement aux produits de ces marques, sinon à toutes les marques",
    )

    @api.depends("of_percent_price_formula")
    def _compute_percent_price(self):
        """Évalue la formule of_percent_price_formula pour remplir le champ percent_price"""
        for line in self:
            price_percent = 100.0
            if line.of_percent_price_formula:
                try:
                    for discount in map(float, line.of_percent_price_formula.replace(",", ".").split("+")):
                        price_percent *= (100 - discount) / 100.0
                except Exception as e:
                    raise UserError(_("Invalid discount formula:\n%s") % line.of_percent_price_formula) from e
            line.percent_price = 100.0 - price_percent

    def _is_applicable_for(self, product, qty_in_product_uom):
        result = super()._is_applicable_for(product, qty_in_product_uom)
        if result:
            if self.of_brand_ids and product.brand_id.id not in self.of_brand_ids.ids:
                return False
        return True
