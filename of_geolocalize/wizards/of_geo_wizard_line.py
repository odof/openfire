# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).


from odoo import fields, models

from odoo.addons.of_geolocalize.models.res_partner import GEOCODING_STATE, OPENSTREETMAP_PRECISION


class OFGeoWizardLines(models.TransientModel):
    _name = 'of.geo.wizard.line'
    _description = "Save geolocalized partners"

    wizard_id = fields.Many2one(comodel_name='of.geo.wizard', string="Wizard")
    partner_id = fields.Many2one(comodel_name='res.partner', string="Partner")
    partner_latitude = fields.Float(string="Geo Latitude", digits=(10, 7))
    partner_longitude = fields.Float(string="Geo Longitude", digits=(10, 7))
    date_localization = fields.Date(string="Geolocation Date")
    response_json = fields.Text(string="Geolocation response")
    geocoding_state = fields.Selection(
        selection=GEOCODING_STATE,
        default='not_tried',
    )
    requested_address = fields.Char(string="Requested address")
    response_address = fields.Char(string="Response address")
    precision = fields.Selection(
        selection=OPENSTREETMAP_PRECISION,
        default='unknown',
        help="Level of geolocalization 's precision",
    )
