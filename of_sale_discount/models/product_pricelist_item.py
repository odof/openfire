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
