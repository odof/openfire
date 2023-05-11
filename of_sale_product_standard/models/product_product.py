# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, models


class Product(models.Model):
    _inherit = 'product.product'

    @api.onchange('of_standard_id')
    def _onchange_of_standard_id(self):
        for product in self:
            product.of_standard_description = product.of_standard_id.description or False
