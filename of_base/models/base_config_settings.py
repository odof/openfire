# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    of_display_city = fields.Boolean(
        string="(OF) Display city",
        config_parameter="of.partner.display_city",
        help="Displays the city in parentheses after the partner name when searching for a partner",
    )
    of_ref_mode = fields.Selection(related="company_id.of_ref_mode", readonly=False, string="(OF) Customer reference")
