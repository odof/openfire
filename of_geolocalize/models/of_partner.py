# -*- coding: utf-8 -*-

#TODO: give "geocode_try_again" other ways to modify the query in order to get a result?

# requires a nominatim server up and running

import json, re
import urllib

from odoo import api, fields, models, _
from odoo.exceptions import UserError

class ResPartner(models.Model):
    _inherit = "res.partner"

    geo_lat = fields.Float(string='Geo Lat', digits=(16, 5))
    geo_lng = fields.Float(string='Geo Lng', digits=(16, 5))
    date_last_localization = fields.Date(string='Last Geolocation Date', readonly=True)
    nominatim_input = fields.Char(string="url sent to Nominatim for geocoding", readonly=True, compute='_compute_nominatim_url', store=False)
    nominatim_response = fields.Text(string="Geocoding Response", readonly=True)
    winning_query = fields.Char(string="modified query that allowed us to geocode",readonly=True)

    geocoding = fields.Selection([
        ('not_tried',"geocoding wasn't attempted for this partner"),
        ('success',"geocoding was a success for this partner"),
        ('success_retry',"initially a failure, geocoding was a success for this partner after a retry using a greedier algorithm"),
        ('failure',"geocoding was a failure for this partner"),
        ('failure_retry',"even after a retry with a greedier algorithm, geocoding was a failure for this partner"),
        ('manual',"this partner's GPS coordinates were allocated manually")
        ], default='not_tried', readonly=True, help="field defining the state of the geocoding for this partner", required=True)

    @api.multi
    def _compute_nominatim_url(self):
        base_url = self.env['ir.config_parameter'].get_param('Nominatim_Base_URL')
        if base_url == 'undefined':
            raise UserError(_('The geocoding server base url is currently undefined, please go to system parameters to define it, or contact your administrator.'))
        else:
            for partner in self:
                params = partner.get_addr_params()

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

                partner.nominatim_input = base_url + query + 'format=json'

    @api.multi
    def get_addr_params(self):
        self.ensure_one()
        result = []
        if (self.street or self.street2):
            if self.country_id:
                result.append(('country',self.country_id.name))
            if self.state_id:
                result.append(('state',self.state_id.name))
            if self.zip:
                result.append(('postalcode',self.zip))
            if self.city:
                result.append(('city',self.city))
            if self.street:
                if self.street2:
                    result.append(('street',self.street + ', ' + self.street2))
                else:
                    result.append(('street',self.street))
            else:
                result.append(('street',self.street2))
        return result

    @api.multi
    def geo_code(self,rewrite=True):
        """
        Method to geocode a partner's address using Nominatim.
        Will not try to geocode if geocoding has already been tried (success or failure), unless 'rewrite' parameter is True.
        Will not try to geocode if GPS coordinates were manually set.
        """
        cmpt = 0
        for partner in self:
            if partner.geocoding not in ('success','success_retry','manual') and (partner.geo_lat != 0 or partner.geo_lng != 0):
                # if geocoding not in ('success','success_retry','manual') and the partner already has GPS coordinates
                # -> they were set outside of this module and should be considered as manually set
                partner.geocoding = 'manual'
            elif ( not partner.geocoding == 'manual' and (rewrite or partner.geocoding == 'not_tried') ):
                try:
                    result = json.load(urllib.urlopen(partner.nominatim_input))
                except Exception as e:
                    raise UserError(_('Cannot contact geolocation servers. Please make sure that your Internet connection is up and running. (error: %s).') % e)

                if result == []:
                    partner.write({
                        'geo_lat': 0,
                        'geo_lng': 0,
                        'date_last_localization': fields.Date.context_today(partner),
                        'geocoding': 'failure',
                        'nominatim_response': "[]"
                    })
                else:
                    partner.write({
                        'geocoding': 'success',
                        'geo_lat': result[0]['lat'],
                        'geo_lng': result[0]['lon'],
                        'date_last_localization': fields.Date.context_today(partner),
                        'nominatim_response': json.dumps(result, indent=3, sort_keys=True, ensure_ascii = False)
                    })
                cmpt += 1
                if cmpt % 100 == 0:
                    self._cr.commit()

        return True

    @api.multi
    def geo_code_retry(self):
        """
        Method to try again to geocode a partner's address using Nominatim.
        Will not try to geocode partners whose GPS coordinates are already set.
        """
        for partner in self:
            if partner.geocoding not in ('success','success_retry','manual'):
                found = False
                query = partner.nominatim_input
                try:
                    result = json.load(urllib.urlopen(query)) # try the usual way in case of modification of the address of a geocoding failure
                except Exception as e:
                    raise UserError(_('Cannot contact geolocation servers. Please make sure that your Internet connection is up and running (%s).') % e)

                if result != []: # success!
                    found = True
                    partner.write({
                        'geocoding': 'success',
                        'geo_lat': result[0]['lat'],
                        'geo_lng': result[0]['lon'],
                        'date_last_localization': fields.Date.context_today(partner),
                        'nominatim_response': json.dumps(result, indent=3, sort_keys=True, ensure_ascii = False),
                    })
                else:
                    # do we have a street of the form <nb> <street> ?
                    with_nb_street = re.search(r"(?P<url>.+)street=(?P<nb>[0-9]+)\+(?P<street1>.+)&format=json",query)
                    if with_nb_street is not None:
                        # do we have a street of the form <nb> <street1>, <street2> ?
                        with_nb_street1_street2 = re.search(r"(?P<url>.+)street=(?P<nb>[0-9]+)\+(?P<street1>.+)%2C\+(?P<street2>.*)&format=json",query)
                        if with_nb_street1_street2 is not None:
                            # replace street=<nb>+<street1>,+<street2> with street=<nb>+<street1>
                            q_nb_street1 = re.sub(r"(?P<url>.+)street=(?P<nb>[0-9]+)\+(?P<street1>.+)%2C\+(?P<street2>.*)&format=json",r"\g<url>street=\g<nb>\+\g<street1>&format=json",query)
                            #print "try 1: replace street=<nb> <street1>, <street2> with street=<nb> <street1>"
                            #print "query: ",q_nb_street1
                            try:
                                result = json.load(urllib.urlopen(q_nb_street1))
                            except Exception as e:
                                raise UserError(_('Cannot contact geolocation servers. Please make sure that your Internet connection is up and running (%s).') % e)

                            if result != []: # success!
                                found = True
                                partner.write({
                                    'geocoding': 'success_retry',
                                    'geo_lat': result[0]['lat'],
                                    'geo_lng': result[0]['lon'],
                                    'date_last_localization': fields.Date.context_today(partner),
                                    'nominatim_response': json.dumps(result, indent=3, sort_keys=True, ensure_ascii = False),
                                    'winning_query': "replace street=<nb> <street1>, <street2> with street=<nb> <street1>",
                                })
                            else: # geocoding failed again
                                # replace street=<nb>+<street1>,+<street2> with street=<street1>
                                q_street1 = re.sub(r"(?P<url>.+)street=(?P<nb>[0-9]+)\+(?P<street1>.+)%2C\+(?P<street2>.*)&format=json",r"\g<url>street=\g<street1>&format=json",query)
                                #print "try 2: replace street=<nb> <street1>, <street2> with street=<street1>"
                                #print "query, ",q_street1
                                try:
                                    result = json.load(urllib.urlopen(q_street1))
                                except Exception as e:
                                    raise UserError(_('Cannot contact geolocation servers. Please make sure that your Internet connection is up and running (%s).') % e)

                                if result != []: # success!
                                    found = True
                                    partner.write({
                                        'geocoding': 'success_retry',
                                        'geo_lat': result[0]['lat'],
                                        'geo_lng': result[0]['lon'],
                                        'date_last_localization': fields.Date.context_today(partner),
                                        'nominatim_response': json.dumps(result, indent=3, sort_keys=True, ensure_ascii = False),
                                        'winning_query': "replace street=<nb> <street1>, <street2> with street=<street1>",
                                    })
                                else: # geocoding failed again
                                    # replace street=<nb>+<street1>,+<street2> with street=<street1>,+<street2>
                                    q_street1_street2 = re.sub(r"(?P<url>.+)street=(?P<nb>[0-9]+)\+(?P<street1>.+)%2C\+(?P<street2>.*)&format=json",r"\g<url>street=\g<street1>%2C\+\g<street2>&format=json",query)
                                    #print "try 3: replace street=<nb> <street1>, <street2> with street=<street1>, <street2>"
                                    #print "query: ",q_street1_street2
                                    try:
                                        result = json.load(urllib.urlopen(q_street1_street2))
                                    except Exception as e:
                                        raise UserError(_('Cannot contact geolocation servers. Please make sure that your Internet connection is up and running (%s).') % e)

                                    if result != []: # success!
                                        found = True
                                        partner.write({
                                            'geocoding': 'success_retry',
                                            'geo_lat': result[0]['lat'],
                                            'geo_lng': result[0]['lon'],
                                            'date_last_localization': fields.Date.context_today(partner),
                                            'nominatim_response': json.dumps(result, indent=3, sort_keys=True, ensure_ascii = False),
                                            'winning_query': "replace street=<nb> <street1>, <street2> with street=<street1>, <street2>",
                                        })
                                    else: #geocoding failed again
                                        # replace street=<nb>+<street1>,+<street2> with street=<street2>
                                        q_street2 = re.sub(r"(?P<url>.+)street=(?P<nb>[0-9]+)\+(?P<street1>.+)%2C\+(?P<street2>.*)&format=json",r"\g<url>street=\g<street2>&format=json",query)
                                        #print "try 4: replace street=<nb> <street1>, <street2> with street=<street2>"
                                        #print "query: ",q_street2
                                        try:
                                            result = json.load(urllib.urlopen(q_street2))
                                        except Exception as e:
                                            raise UserError(_('Cannot contact geolocation servers. Please make sure that your Internet connection is up and running (%s).') % e)

                                        if result != []: # success!
                                            found = True
                                            partner.write({
                                                'geocoding': 'success_retry',
                                                'geo_lat': result[0]['lat'],
                                                'geo_lng': result[0]['lon'],
                                                'date_last_localization': fields.Date.context_today(partner),
                                                'nominatim_response': json.dumps(result, indent=3, sort_keys=True, ensure_ascii = False),
                                                'winning_query': "replace street=<nb> <street1>, <street2> with street=<street2>",
                                            })
                        else: # we have a number but we don't have a street2
                            # replace street=<nb>+<street> with street=<street>
                            q_street = re.sub(r"(?P<url>.+)street=(?P<nb>[0-9]+)\+(?P<street1>.+)&format=json",r"\g<url>street=\g<street1>&format=json",query)
                            #print "try 5: replace street=<nb> <street> with street=<street>"
                            #print "query: ",q_street
                            try:
                                result = json.load(urllib.urlopen(q_street))
                            except Exception as e:
                                raise UserError(_('Cannot contact geolocation servers. Please make sure that your Internet connection is up and running (%s).') % e)

                            if result != []: # success!
                                found = True
                                partner.write({
                                    'geocoding': 'success_retry',
                                    'geo_lat': result[0]['lat'],
                                    'geo_lng': result[0]['lon'],
                                    'date_last_localization': fields.Date.context_today(partner),
                                    'nominatim_response': json.dumps(result, indent=3, sort_keys=True, ensure_ascii = False),
                                    'winning_query': "replace street=<nb> <street> with street=<street>",
                                })

                    # do we have a street of the form <street1>, <street2> ?
                    elif re.search(r"(?P<url>.+)street=(?P<street1>.+)%2C\+(?P<street2>.*)&format=json",query) is not None: # geocoding failed again
                        # replace street=<street1>,+<street2> with street=<street1>
                        q_street1 = re.sub(r"(?P<url>.+)street=(?P<street1>.+)%2C\+(?P<street2>.*)&format=json",r"\g<url>street=\g<street1>&format=json",query)
                        #print "try 6: replace street=<street1>, <street2> with street=<street1>"
                        #print "query: ",q_street1
                        try:
                            result = json.load(urllib.urlopen(q_street1))
                        except Exception as e:
                            raise UserError(_('Cannot contact geolocation servers. Please make sure that your Internet connection is up and running (%s).') % e)

                        if result != []: # success!
                            found = True
                            partner.write({
                                'geocoding': 'success_retry',
                                'geo_lat': result[0]['lat'],
                                'geo_lng': result[0]['lon'],
                                'date_last_localization': fields.Date.context_today(partner),
                                'nominatim_response': json.dumps(result, indent=3, sort_keys=True, ensure_ascii = False),
                                'winning_query': "replace street=<street1>, <street2> with street=<street1>",
                            })
                        else: # geocoding failed yet again
                            # replace street=<street1>,+<street2> with street=<street2>
                            q_street2 = re.sub(r"(?P<url>.+)street=(?P<street1>.+)%2C\+(?P<street2>.*)&format=json",r"\g<url>street=\g<street2>&format=json",query)
                            #print "try 7: replace street=<street1>, <street2> with street=<street2>"
                            #print "query: ",q_street2
                            try:
                                result = json.load(urllib.urlopen(q_street2))
                            except Exception as e:
                                raise UserError(_('Cannot contact geolocation servers. Please make sure that your Internet connection is up and running (%s).') % e)

                            if result != []: # success!
                                found = True
                                partner.write({
                                    'geocoding': 'success_retry',
                                    'geo_lat': result[0]['lat'],
                                    'geo_lng': result[0]['lon'],
                                    'date_last_localization': fields.Date.context_today(partner),
                                    'nominatim_response': json.dumps(result, indent=3, sort_keys=True, ensure_ascii = False),
                                    'winning_query': "replace street=<street1>, <street2> with street=<street2>",
                                })
                if not found:
                    partner.geocoding = 'failure_retry'


    #will compute the lat and lng when a partner is created
    @api.model
    def create(self, vals):
        """
        On creation of a partner, Will try to geocode if an address is specified.
        Will not try to geocode if GPS coordinates are specified, in that case will set 'geocoding' field to 'manual'.
        """
        partner = super(ResPartner,self).create(vals)
        if partner.geo_lat == 0 and partner.geo_lng == 0 and (partner.street or partner.street2) and partner.zip and partner.city: 
            partner.geo_code()
        elif partner.geo_lat != 0 or partner.geo_lng != 0:
            partner.geocoding = 'manual'

        return partner

    #will recompute the lat and lng when a partner's address is modified
    @api.multi
    def write(self, vals):
        """
        Override
        Case geocoding_success didn't change and either geo_lat or geo_lng changed: the partner was localized manually.
        Case address changed: we will try to geocode the newly set address
        """
        if 'geocoding' not in vals and ('geo_lat' in vals or 'geo_lng' in vals) and vals['geo_lat'] != 0:
            vals['geocoding'] = 'manual'

        super(ResPartner,self).write(vals)

        if len(self._ids) == 1:
            if self.geocoding != 'manual':
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

