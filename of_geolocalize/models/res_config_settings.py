# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    geocoding_on_write = fields.Selection(
        selection=[
            ("no", "Do not recalculate geocoding values automatically (GPS coordinates are reset to zero)"),
            ("yes", "Recalculate automatically geocoding values"),
        ],
        config_parameter="of.geolocalize.geocoding_on_write",
        string="If an address is changed",
        help="Recalculate geocoding values automatically when a partner's address is changed",
    )

    geocoding_on_create = fields.Selection(
        selection=[
            ("no", "Do not calculate geocoding values (recommended before importing a large number of partners)"),
            ("yes", "Calculate geocoding values automatically"),
        ],
        config_parameter="of.geolocalize.geocoding_on_create",
        string="If a partner is added",
        help="Calculate geocoding values automatically when a new partner is added",
    )
    timeout = fields.Integer(
        config_parameter="of.geolocalize.timeout",
    )
