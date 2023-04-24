# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import _, api, fields, models
from odoo.exceptions import UserError


class ProductCategory(models.Model):
    _inherit = 'product.category'

    of_margin_rate = fields.Integer(
        string="Margin rate",
        help="Minimum recommended % margin rate when the main product of a quote is in the category.",
    )

    @api.constrains('of_margin_rate')
    def _constraint_of_margin_rate(self):
        for category in self:
            if category.of_margin_rate < 0 or category.of_margin_rate > 100:
                raise UserError(_("The margin rate must be between 0% and 100%."))
