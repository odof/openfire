# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class ResConfigSetting(models.TransientModel):
    _inherit = "res.config.settings"

    of_sale_order_margin_control = fields.Boolean(
        string="(OF) Margin control",
        help="Enable margin control at order validation",
        config_parameter="of.sale.margin.of_sale_order_margin_control",
    )
