# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    group_product_variant_specific_price = fields.Boolean(
        string="(OF) Handle pricing by variant",
        implied_group='of_product.group_product_variant_specific_price',
        compute='_compute_group_product_variant_specific_price',
        store=True,
        readonly=False,
    )
    of_product_variant_specific_price = fields.Selection(
        selection=[
            ('by_attribute', "Handle pricing by attribute"),
            ('by_variant', "Handle pricing by variant"),
        ],
        string="(OF) Manage Product variant pricing",
        required=True,
        default='by_attribute',
        config_parameter='of.product.of_product_variant_specific_price',
    )

    @api.depends('of_product_variant_specific_price')
    def _compute_group_product_variant_specific_price(self):
        for wizard in self:
            wizard.group_product_variant_specific_price = wizard.of_product_variant_specific_price == 'by_variant'
