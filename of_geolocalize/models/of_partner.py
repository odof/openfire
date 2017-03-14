# -*- coding: utf-8 -*-

# reworking of module base_geolocalize so that it doesn't use google

#TODO: change the URL to use a local version of Nominatim
# requires a gis database

import json
import urllib

from odoo import api, fields, models, tools, _
from odoo.exceptions import UserError


# get the lat and lng out of an address using Nominatim
def addr2LatLng(addr):
    url = 'https://nominatim.openstreetmap.org/search?format=json&q='
    url += urllib.quote(addr.encode('utf8'))
    
    try:
        result = json.load(urllib.urlopen(url))
    except Exception as e:
        raise UserError(_('Cannot contact geolocation servers. Please make sure that your Internet connection is up and running (%s).') % e)

    if result == []:
        return None

    try:
        #json format
        latLng = [result[0]['lat'],result[0]['lon']]
        return latLng
    except (KeyError, ValueError):
        return None
    
def geo_query_addr(street=None, street2=None, zip=None, city=None, state=None, country=None):
    if country and ',' in country and (country.endswith(' of') or country.endswith(' of the')):
        # put country qualifier in front, otherwise GMap gives wrong results,
        # e.g. 'Congo, Democratic Republic of the' => 'Democratic Republic of the Congo'
        country = '{1} {0}'.format(*country.split(',', 1))
    return tools.ustr(', '.join(filter(None, [street,
                                              street2,
                                              ("%s %s" % (zip or '', city or '')).strip(),
                                              state,
                                              country])))

class ResPartner(models.Model):
    _inherit = "res.partner"

    geo_lat = fields.Float(string='Geo Lat', digits=(16, 5))
    geo_lng = fields.Float(string='Geo Lng', digits=(16, 5))
    date_last_localization = fields.Date(string='Last Geolocation Date')

    @api.multi
    def geo_code(self):
        # We need country names in English below
        # at least google does, didn't check if Nominatim does too
        for partner in self.with_context(lang='en_US'):
            result = addr2LatLng(geo_query_addr(street=partner.street,
                                                   street2=partner.street2,
                                                zip=partner.zip,
                                                city=partner.city,
                                                state=partner.state_id.name,
                                                country=partner.country_id.name))
            if result is None:
                result = addr2LatLng(geo_query_addr(
                    city=partner.city,
                    state=partner.state_id.name,
                    country=partner.country_id.name
                ))

            if result:
                partner.write({
                    'geo_lat': result[0],
                    'geo_lng': result[1],
                    'date_last_localization': fields.Date.context_today(partner)
                })
                
        return True
    
    #will compute the lat and lng when a partner is created
    @api.model
    def create(self, vals):
        partner = super(ResPartner,self).create(vals)
        if not (partner.geo_lat and partner.geo_lng) and (partner.street or partner.street2) and partner.zip and partner.city and partner.country: 
            partner.geo_code()
        return partner

    #will recompute the lat and lng when a partner's address is modified
    @api.multi
    def write(self, vals):
        super(ResPartner,self).write(vals)
        for key in vals:
            if key in ('street', 'street2', 'city', 'state_id', 'country_id', 'zip'):
                self.geo_code()
                break
        return True

