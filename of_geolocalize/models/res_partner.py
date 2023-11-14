# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, models


class ResPartner(models.Model):
    _inherit = 'res.partner'

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

        result = super().write(vals)
        if to_update:
            if geocoding_on_write_value == 'yes':
                to_update.geo_localize()
            else:
                vals = {
                    'partner_latitude': 0.0,
                    'partner_longitude': 0.0,
                }
                to_update.write(vals)
        return result
