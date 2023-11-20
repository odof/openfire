# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import json

from odoo import _, api, fields, models
from odoo.tools import config


class ResPartner(models.Model):
    _inherit = 'res.partner'

    of_response_json = fields.Text(string="Geolocation response")
    of_geocoding_state = fields.Selection(
        selection=[
            ('not_tried', "Not Tried"),
            ('success', "Success"),
            ('failure', "Failure"),
            ('manual', "Manual"),
        ],
        default='not_tried',
        string="Geocoding State",
    )

    def geo_localize(self):
        """Override to add custom OF fields"""
        if not self._context.get('force_geo_localize') and (
            self._context.get('import_file')
            or any(config[key] for key in ['test_enable', 'test_file', 'init', 'update'])
        ):
            return False
        partners_not_geo_localized = self.env['res.partner']
        for partner in self.with_context(lang='en_US'):
            if result := self._geo_localize(
                partner.street,
                partner.zip,
                partner.city,
                partner.state_id.name,
                partner.country_id.name,
            ):
                partner.write(
                    {
                        'partner_latitude': result[0],
                        'partner_longitude': result[1],
                        'date_localization': fields.Date.context_today(partner),
                        'of_response_json': json.dumps(result[2][0], indent=3, sort_keys=True, ensure_ascii=False),
                        'of_geocoding_state': 'success',
                    }
                )
            else:
                partners_not_geo_localized |= partner
        if partners_not_geo_localized:
            self.env['bus.bus']._sendone(
                self.env.user.partner_id,
                'simple_notification',
                {
                    'title': _("Warning"),
                    'message': _(
                        'No match found for %(partner_names)s address(es).',
                        partner_names=', '.join(partners_not_geo_localized.mapped('name')),
                    ),
                },
            )
        return True

    @api.model_create_multi
    def create(self, vals_list):
        partners = super(ResPartner, self).create(vals_list)
        geocoding_on_create_value = (
            self.env['ir.config_parameter'].sudo().get_param('of.geolocalize.geocoding_on_create')
        )
        if geocoding_on_create_value == 'yes':
            partners.geo_localize()
        return partners

    def write(self, vals):
        geocoding_on_write_value = self.env['ir.config_parameter'].sudo().get_param('of.geolocalize.geocoding_on_write')
        to_update = self.env['res.partner']
        if any(
            field in vals
            for field in (
                'street',
                'street2',
                'zip',
                'city',
                'state_id',
                'country_id',
            )
        ) and any(f'partner_{field}' not in vals for field in ['latitude', 'longitude']):
            for partner in self:
                for key in ('street', 'street2', 'zip', 'city'):
                    if key in vals and partner[key] != vals[key]:
                        to_update |= partner
                        break
                else:
                    for key in ('state_id', 'country_id'):
                        if key in vals and partner[key].id != vals[key]:
                            to_update |= partner
                            break
        if any(field in vals for field in ['partner_latitude', 'partner_longitude']):
            self.of_geocoding_state = 'manual'

        # Reset json in to update of_response_json and of_geocoding_state
        if any(field in vals for field in ['street', 'zip', 'city', 'state_id', 'country_id']) and any(
            f'partner_{field}' not in vals for field in ['latitude', 'longitude']
        ):
            vals.update(
                {
                    'of_response_json': "",
                    'of_geocoding_state': 'failure',
                }
            )
        result = super().write(vals)
        if to_update:
            if geocoding_on_write_value == 'yes':
                to_update.geo_localize()
            else:
                vals = {
                    'partner_latitude': 0.0,
                    'partner_longitude': 0.0,
                    'of_response_json': "",
                    'of_geocoding_state': 'failure',
                }
                to_update.write(vals)
        return result
