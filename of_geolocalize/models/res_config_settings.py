# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    geocoding_on_write = fields.Selection(
        selection=[
            (
                'no',
                "Do not recalculate geocoding values automatically "
                "(GPS coordinates are reset to zero if not entered at the same time.)",
            ),
            (
                'yes',
                "Recalculate geocoding values (Geocoding is attempted if GPS coordinates \
                    are not entered at the same time.)",
            ),
        ],
        string="If an address is changed",
        help="Recalculate geocoding values automatically when a partner's address is changed",
        config_parameter="of.geolocalize.geocoding_on_write",
    )

    geocoding_on_create = fields.Selection(
        selection=[
            ('no', "Do not calculate geocoding values (recommended when a large number of partners are imported)"),
            ('yes', "Calculate geocoding values automatically"),
        ],
        string="If a partner is added",
        help="Calculate geocoding values automatically when a new partner is added",
        config_parameter="of.geolocalize.geocoding_on_create",
    )
