# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    group_product_variant_specific_price = fields.Boolean(
        string="(OF) Handle pricing by variant", implied_group='of_product.group_product_variant_specific_price'
    )
