# -*- coding: utf-8 -*-

# TODO: give "geocode_try_again" other ways to modify the query in order to get a result?

# requires a nominatim server up and running

import json
import re
import urllib

from odoo import api, fields, models, _
from odoo.exceptions import UserError
import logging
_logger = logging.getLogger(__name__)

class OfGeolocalize(models.AbstractModel):
    _name = "of.geolocalize"

    geo_lat = fields.Float(string='Geo Lat', digits=(8, 8), help="latitude field")
    geo_lng = fields.Float(string='Geo Lng', digits=(8, 8), help="longitude field")
    date_last_localization = fields.Date(string='Last Geolocation Date', readonly=True)
    nominatim_input = fields.Char(string="url sent to Nominatim for geocoding", readonly=True)
    nominatim_response = fields.Text(string="Geocoding Response", readonly=True)
    winning_query = fields.Char(string="modified query that allowed us to geocode", readonly=True)
    nominatim_public = fields.Boolean(string="Geocoding server address set to public instance of Nominatim", readonly=True, compute="_check_nominatim_URL", store=False)

    geocoding = fields.Selection([
        ('not_tried', "geocoding wasn't attempted for this partner"),
        ('success', "geocoding was a success for this partner"),
        ('success_retry', "initially a failure, geocoding was a success for this partner after a retry using a greedier algorithm"),
        ('failure', "geocoding was a failure for this partner"),
        ('failure_retry', "even after a retry with a greedier algorithm, geocoding was a failure for this partner"),
        ('manual', "this partner's GPS coordinates were allocated manually")
        ], default='not_tried', readonly=True, help="field defining the state of the geocoding for this partner", required=True)

    @api.multi
    def _compute_nominatim_url(self):
        base_url = self.env['ir.config_parameter'].get_param('Nominatim_Base_URL')
        # TODO: re-refléchir ce fonctionnement
        if not base_url:
            base_url = 'https://nominatim.openstreetmap.org/search'
        for record in self:
            params = record.get_addr_params()

            query = "?"
            country = ""

            for p in params:
                if p[0] == "country":
                    country = p[1]
                if p[0] == "postalcode" and country.upper() == "FRANCE":
                    # for french postal codes, taking only the 2 first digits seems to give us better results for some reason
                    query += urllib.quote_plus(p[0].encode('utf8')) + "=" + urllib.quote_plus(p[1][:2].encode('utf8')) + "&"
                else:
                    query += p[0].encode('utf8') + "=" + urllib.quote_plus((p[1].strip()).encode('utf8')) + "&"

            record.nominatim_input = base_url + query + 'format=json'

    @api.multi
    def get_addr_params(self):
        raise NotImplementedError

    @api.multi
    def _check_nominatim_URL(self):
        for partner in self:
            partner.nominatim_public = partner.env['ir.config_parameter'].get_param('Nominatim_Base_URL') == 'https://nominatim.openstreetmap.org/search'

    @api.multi
    def geo_code(self, rewrite=True, nominatim_checked=False):
        """
        Method to geocode a record's address using Nominatim.
        Will not try to geocode if geocoding has already been tried (success or failure), unless 'rewrite' parameter is True.
        Will not try to geocode if GPS coordinates were manually set.
        """
        cmpt = 0
        for record in self:
            if record.geocoding not in ('success', 'success_retry', 'manual') and (record.geo_lat != 0 or record.geo_lng != 0):
                # if geocoding not in ('success','success_retry','manual') and the partner already has GPS coordinates
                #     -> they were set outside of this module (before installation of the module for example)
                #     therefore we try geocoding the address and set geocoding to 'manual' if geocoding fails
                record._compute_nominatim_url()
                try:
                    result = json.load(urllib.urlopen(record.nominatim_input))
                except Exception as e:
                    raise UserError(_('Cannot contact geolocation servers. Please make sure that your Internet connection is up and running. (error: %s).') % e)

                if result == []:
                    record.write({
                        'date_last_localization': fields.Date.context_today(record),
                        'geocoding': 'manual',
                        'nominatim_response': "[]"
                    })
                else:
                    record.write({
                        'geocoding': 'success',
                        'geo_lat': result[0]['lat'],
                        'geo_lng': result[0]['lon'],
                        'date_last_localization': fields.Date.context_today(record),
                        'nominatim_response': json.dumps(result, indent=3, sort_keys=True, ensure_ascii=False)
                    })
            elif (record.geocoding != 'manual' and (rewrite or record.geocoding == 'not_tried')):
                record._compute_nominatim_url()
                try:
                    result = json.load(urllib.urlopen(record.nominatim_input))
                except Exception as e:
                    raise UserError(_('Cannot contact geolocation servers. Please make sure that your Internet connection is up and running. (error: %s).') % e)

                if result == []:
                    record.write({
                        'geo_lat': 0,
                        'geo_lng': 0,
                        'date_last_localization': fields.Date.context_today(record),
                        'geocoding': 'failure',
                        'nominatim_response': "[]"
                    })
                else:
                    record.write({
                        'geocoding': 'success',
                        'geo_lat': result[0]['lat'],
                        'geo_lng': result[0]['lon'],
                        'date_last_localization': fields.Date.context_today(record),
                        'nominatim_response': json.dumps(result, indent=3, sort_keys=True, ensure_ascii=False)
                    })
                cmpt += 1
                if cmpt % 100 == 0:
                    self._cr.commit()

        return True

    @api.multi
    def geo_code_retry(self):
        """
        Method to try again to geocode a record's address using Nominatim.
        Will not try to geocode partners whose GPS coordinates are already set.
        """
        for record in self:
            if record.geocoding not in ('success', 'success_retry', 'manual'):
                found = False
                record._compute_nominatim_url()
                query = record.nominatim_input
                try:
                    result = json.load(urllib.urlopen(query))  # try the usual way in case of modification of the address of a geocoding failure
                except Exception as e:
                    raise UserError(_('Cannot contact geolocation servers. Please make sure that your Internet connection is up and running (%s).') % e)

                if result != []:  # success!
                    found = True
                    record.write({
                        'geocoding': 'success',
                        'geo_lat': result[0]['lat'],
                        'geo_lng': result[0]['lon'],
                        'date_last_localization': fields.Date.context_today(record),
                        'nominatim_response': json.dumps(result, indent=3, sort_keys=True, ensure_ascii=False),
                    })
                else:
                    # do we have a street of the form <nb> <street> ?
                    with_nb_street = re.search(r"(?P<url>.+)street=(?P<nb>[0-9]+)\+(?P<street1>.+)&format=json", query)
                    if with_nb_street is not None:
                        # do we have a street of the form <nb> <street1>, <street2> ?
                        with_nb_street1_street2 = re.search(r"(?P<url>.+)street=(?P<nb>[0-9]+)\+(?P<street1>.+)%2C\+(?P<street2>.*)&format=json", query)
                        if with_nb_street1_street2 is not None:
                            # replace street=<nb>+<street1>,+<street2> with street=<nb>+<street1>
                            q_nb_street1 = re.sub(r"(?P<url>.+)street=(?P<nb>[0-9]+)\+(?P<street1>.+)%2C\+(?P<street2>.*)&format=json", r"\g<url>street=\g<nb>\+\g<street1>&format=json", query)
                            # print "try 1: replace street=<nb> <street1>, <street2> with street=<nb> <street1>"
                            # print "query: ",q_nb_street1
                            try:
                                result = json.load(urllib.urlopen(q_nb_street1))
                            except Exception as e:
                                raise UserError(_('Cannot contact geolocation servers. Please make sure that your Internet connection is up and running (%s).') % e)

                            if result != []:  # success!
                                found = True
                                record.write({
                                    'geocoding': 'success_retry',
                                    'geo_lat': result[0]['lat'],
                                    'geo_lng': result[0]['lon'],
                                    'date_last_localization': fields.Date.context_today(record),
                                    'nominatim_response': json.dumps(result, indent=3, sort_keys=True, ensure_ascii=False),
                                    'winning_query': "replace street=<nb> <street1>, <street2> with street=<nb> <street1>",
                                })
                            else:  # geocoding failed again
                                # replace street=<nb>+<street1>,+<street2> with street=<street1>
                                q_street1 = re.sub(r"(?P<url>.+)street=(?P<nb>[0-9]+)\+(?P<street1>.+)%2C\+(?P<street2>.*)&format=json", r"\g<url>street=\g<street1>&format=json", query)
                                # print "try 2: replace street=<nb> <street1>, <street2> with street=<street1>"
                                # print "query, ",q_street1
                                try:
                                    result = json.load(urllib.urlopen(q_street1))
                                except Exception as e:
                                    raise UserError(_('Cannot contact geolocation servers. Please make sure that your Internet connection is up and running (%s).') % e)

                                if result != []:  # success!
                                    found = True
                                    record.write({
                                        'geocoding': 'success_retry',
                                        'geo_lat': result[0]['lat'],
                                        'geo_lng': result[0]['lon'],
                                        'date_last_localization': fields.Date.context_today(record),
                                        'nominatim_response': json.dumps(result, indent=3, sort_keys=True, ensure_ascii=False),
                                        'winning_query': "replace street=<nb> <street1>, <street2> with street=<street1>",
                                    })
                                else:  # geocoding failed again
                                    # replace street=<nb>+<street1>,+<street2> with street=<street1>,+<street2>
                                    q_street1_street2 = re.sub(r"(?P<url>.+)street=(?P<nb>[0-9]+)\+(?P<street1>.+)%2C\+(?P<street2>.*)&format=json", r"\g<url>street=\g<street1>%2C\+\g<street2>&format=json", query)
                                    # print "try 3: replace street=<nb> <street1>, <street2> with street=<street1>, <street2>"
                                    # print "query: ",q_street1_street2
                                    try:
                                        result = json.load(urllib.urlopen(q_street1_street2))
                                    except Exception as e:
                                        raise UserError(_('Cannot contact geolocation servers. Please make sure that your Internet connection is up and running (%s).') % e)

                                    if result != []:  # success!
                                        found = True
                                        record.write({
                                            'geocoding': 'success_retry',
                                            'geo_lat': result[0]['lat'],
                                            'geo_lng': result[0]['lon'],
                                            'date_last_localization': fields.Date.context_today(record),
                                            'nominatim_response': json.dumps(result, indent=3, sort_keys=True, ensure_ascii=False),
                                            'winning_query': "replace street=<nb> <street1>, <street2> with street=<street1>, <street2>",
                                        })
                                    else:  # geocoding failed again
                                        # replace street=<nb>+<street1>,+<street2> with street=<street2>
                                        q_street2 = re.sub(r"(?P<url>.+)street=(?P<nb>[0-9]+)\+(?P<street1>.+)%2C\+(?P<street2>.*)&format=json", r"\g<url>street=\g<street2>&format=json", query)
                                        # print "try 4: replace street=<nb> <street1>, <street2> with street=<street2>"
                                        # print "query: ",q_street2
                                        try:
                                            result = json.load(urllib.urlopen(q_street2))
                                        except Exception as e:
                                            raise UserError(_('Cannot contact geolocation servers. Please make sure that your Internet connection is up and running (%s).') % e)

                                        if result != []:  # success!
                                            found = True
                                            record.write({
                                                'geocoding': 'success_retry',
                                                'geo_lat': result[0]['lat'],
                                                'geo_lng': result[0]['lon'],
                                                'date_last_localization': fields.Date.context_today(record),
                                                'nominatim_response': json.dumps(result, indent=3, sort_keys=True, ensure_ascii=False),
                                                'winning_query': "replace street=<nb> <street1>, <street2> with street=<street2>",
                                            })
                        else:  # we have a number but we don't have a street2
                            # replace street=<nb>+<street> with street=<street>
                            q_street = re.sub(r"(?P<url>.+)street=(?P<nb>[0-9]+)\+(?P<street1>.+)&format=json", r"\g<url>street=\g<street1>&format=json", query)
                            # print "try 5: replace street=<nb> <street> with street=<street>"
                            # print "query: ",q_street
                            try:
                                result = json.load(urllib.urlopen(q_street))
                            except Exception as e:
                                raise UserError(_('Cannot contact geolocation servers. Please make sure that your Internet connection is up and running (%s).') % e)

                            if result != []:  # success!
                                found = True
                                record.write({
                                    'geocoding': 'success_retry',
                                    'geo_lat': result[0]['lat'],
                                    'geo_lng': result[0]['lon'],
                                    'date_last_localization': fields.Date.context_today(record),
                                    'nominatim_response': json.dumps(result, indent=3, sort_keys=True, ensure_ascii=False),
                                    'winning_query': "replace street=<nb> <street> with street=<street>",
                                })

                    # do we have a street of the form <street1>, <street2> ?
                    elif re.search(r"(?P<url>.+)street=(?P<street1>.+)%2C\+(?P<street2>.*)&format=json", query) is not None:  # geocoding failed again
                        # replace street=<street1>,+<street2> with street=<street1>
                        q_street1 = re.sub(r"(?P<url>.+)street=(?P<street1>.+)%2C\+(?P<street2>.*)&format=json", r"\g<url>street=\g<street1>&format=json", query)
                        # print "try 6: replace street=<street1>, <street2> with street=<street1>"
                        # print "query: ",q_street1
                        try:
                            result = json.load(urllib.urlopen(q_street1))
                        except Exception as e:
                            raise UserError(_('Cannot contact geolocation servers. Please make sure that your Internet connection is up and running (%s).') % e)

                        if result != []:  # success!
                            found = True
                            record.write({
                                'geocoding': 'success_retry',
                                'geo_lat': result[0]['lat'],
                                'geo_lng': result[0]['lon'],
                                'date_last_localization': fields.Date.context_today(record),
                                'nominatim_response': json.dumps(result, indent=3, sort_keys=True, ensure_ascii=False),
                                'winning_query': "replace street=<street1>, <street2> with street=<street1>",
                            })
                        else:  # geocoding failed yet again
                            # replace street=<street1>,+<street2> with street=<street2>
                            q_street2 = re.sub(r"(?P<url>.+)street=(?P<street1>.+)%2C\+(?P<street2>.*)&format=json", r"\g<url>street=\g<street2>&format=json", query)
                            # print "try 7: replace street=<street1>, <street2> with street=<street2>"
                            # print "query: ",q_street2
                            try:
                                result = json.load(urllib.urlopen(q_street2))
                            except Exception as e:
                                raise UserError(_('Cannot contact geolocation servers. Please make sure that your Internet connection is up and running (%s).') % e)

                            if result != []:  # success!
                                found = True
                                record.write({
                                    'geocoding': 'success_retry',
                                    'geo_lat': result[0]['lat'],
                                    'geo_lng': result[0]['lon'],
                                    'date_last_localization': fields.Date.context_today(record),
                                    'nominatim_response': json.dumps(result, indent=3, sort_keys=True, ensure_ascii=False),
                                    'winning_query': "replace street=<street1>, <street2> with street=<street2>",
                                })
                if not found:
                    record.geocoding = 'failure_retry'

    @api.multi
    def reset_geo_values(self):
        self.write({
            'geo_lat': 0,
            'geo_lng': 0,
            'geocoding': 'not_tried',
            'winning_query': False,
            'nominatim_response': False,
            })

    @api.multi
    def dummy_function(self):
        return True

class ResPartner(models.Model):
    _name = "res.partner"
    _inherit = ["res.partner", "of.geolocalize"]

    @api.multi
    def get_addr_params(self):
        self.ensure_one()
        result = []
        if (self.street or self.street2):
            if self.country_id:
                result.append(('country', self.country_id.name))
            else:
                # search for France if no country is specified
                result.append(('country', 'France'))
            if self.state_id:
                result.append(('state', self.state_id.name))
            if self.zip:
                result.append(('postalcode', self.zip))
            if self.city:
                result.append(('city', self.city))
            if self.street:
                if self.street2:
                    result.append(('street', self.street + ', ' + self.street2))
                else:
                    result.append(('street', self.street))
            else:
                result.append(('street', self.street2))
        return result

    # will compute the lat and lng when a partner is created
    # TODO: gérer le cas: création d'un partenaire avec à la fois une adresse et des coordonnées GPS
    @api.model
    def create(self, vals):
        """
        On creation of a partner, Will try to geocode if an address is specified.
        """
        # if ((vals['street'] or vals['street2']) and vals['zip'] and vals['city'] and (vals['geo_lat'] or vals['geo_lng'])):
        #     partner created with both address and GPS coordinates
        #     pass

        partner = super(ResPartner, self).create(vals)
        # inhiber sur imports et autres
        if not self._context.get('from_import') and not self._context.get('inhiber_geocode') and \
          partner.env['ir.config_parameter'].get_param('Deactivate_Geocoding_On_Create') == "0":
            if (partner.street or partner.street2) and partner.zip and partner.city:
                partner.geo_code()

        return partner

    # will recompute the lat and lng when a partner's address is modified
    @api.multi
    def write(self, vals):
        """
        Override
        Case geocoding didn't change and either geo_lat or geo_lng changed: the partner was localized manually.
        Case address changed: we will try to geocode the newly set address
        """
        if not self._context.get('from_import') and not self._context.get('inhiber_geocode') and \
          self.env['ir.config_parameter'].get_param('Deactivate_Geocoding_On_Write') == "0":
            if 'geocoding' not in vals and ( ('geo_lat' in vals and vals.get('geo_lat') != 0) or ('geo_lng' in vals and vals.get('geo_lng') != 0) ):
                vals['geocoding'] = 'manual'

        super(ResPartner, self).write(vals)

        if len(self._ids) == 1:
            if not self._context.get('from_import') and not self._context.get('inhiber_geocode') and \
              self.geocoding != 'manual' and self.env['ir.config_parameter'].get_param('Deactivate_Geocoding_On_Write') == "0":
                for key in vals:
                    if key in ('street', 'street2', 'city', 'state_id', 'country_id', 'zip'):
                        if self.geocoding == 'failure' or self.geocoding == 'failure_retry':
                            self.reset_geo_values()
                            self.geo_code_retry()
                        else:
                            self.reset_geo_values()
                            self.geo_code()
                        break
        return True
