# -*- coding: utf-8 -*-

# requires a nominatim server

import json
import urllib

from odoo import api, fields, models, _
from odoo.exceptions import UserError

class ResCompany(models.Model):
    _inherit = "res.company"

    geo_lat = fields.Float(string='Geo Lat', digits=(16, 5))
    geo_lng = fields.Float(string='Geo Lng', digits=(16, 5))
    date_last_localization = fields.Date(string='Geolocation Date', readonly=True)

    nominatim_input = fields.Char(string="url sent to Nominatim for geocoding", readonly=True)
    nominatim_public = fields.Boolean(string="Geocoding server address set to public instance of Nominatim", readonly=True, compute="_check_nominatim_URL", store=False)
    geocoding = fields.Selection([
        ('not_tried',"geocoding wasn't attempted for this partner"),
        ('success',"geocoding was a success for this partner"),
        ('failure',"geocoding was a failure for this partner"),
        ('manual',"this partner's GPS coordinates were allocated manually")
        ], default='not_tried', readonly=True, help="field defining the state of the geocoding for this partner", required=True)

    date_last_partner_localization = fields.Date(string='Partner Geolocation Date', readonly=True)
    nb_partners = fields.Integer(string='Number of Partners', compute='_compute_partners_localization_stats', store=False, readonly=True)
    nb_geocoding_success = fields.Integer(string='Number of localized Partners', compute='_compute_partners_localization_stats', store=False, readonly=True)
    nb_geocoding_success_retry = fields.Integer(string='Number of Partners localized using greedier algorithm', compute='_compute_partners_localization_stats', store=False, readonly=True)
    nb_manually_localized_partners = fields.Integer(string='Number of manually localized Partners', compute='_compute_partners_localization_stats', store=False, readonly=True)
    nb_left_to_geocode = fields.Integer(string='Number of partners yet to be localized', compute='_compute_partners_localization_stats', store=False, readonly=True)
    nb_geocoding_failure = fields.Integer(string='Number of partners we tried and failed to geocode', compute='_compute_partners_localization_stats', store=False, readonly=True)
    nb_geocoding_failure_retry = fields.Integer(string='Number of partners we tried and failed to geocode using greedier algorithm', compute='_compute_partners_localization_stats', store=False, readonly=True)

    @api.multi
    def _check_nominatim_URL(self):
        for company in self:
            company.nominatim_public = self.env['ir.config_parameter'].get_param('Nominatim_Base_URL') == 'https://nominatim.openstreetmap.org/search'

    @api.multi
    def _compute_nominatim_url(self):
        base_url = self.env['ir.config_parameter'].get_param('Nominatim_Base_URL')
        for company in self:
            params = company.get_addr_params()

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

            company.nominatim_input = base_url + query + 'format=json'

    @api.multi
    def get_addr_params(self):
        """
        returns a list of tuples containing parameters in order to compute nominatim URL input
        """
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

    # localize every partner of current company, will not geocode partner with existing lat and lng
    @api.multi
    def geo_code_partners(self):
        """
        Method to try geocoding all partners who were not manually localized or already tried.
        """
        partner_obj = self.env["res.partner"] # on récupère tous les partners
        for company_id in self._ids:
            partners = partner_obj.search([('company_id', 'child_of', company_id)]) #critère de selection : cette company est associée
            partners.geo_code(rewrite=False)
        self.write({'date_last_partner_localization': fields.Date.context_today(self)})

    # localize every partner of current company, will geocode partner with existing lat and lng
    @api.multi
    def geo_code_partners_rewrite(self):
        """
        Method to try geocoding all partners who were not manually localized
        """
        partner_obj = self.env["res.partner"] # on récupère tous les partners
        for company_id in self._ids:
            partners = partner_obj.search([('company_id', 'child_of', company_id)]) #critère de selection : cette company est associée
            partners.geo_code(rewrite=True)
        self.write({'date_last_partner_localization': fields.Date.context_today(self)})

    # localize every partner of current company, will not geocode partner with existing lat and lng. Will use greedier algorithm
    @api.multi
    def geo_code_partners_retry(self):
        """
        Method to try geocoding all partners not yet localized using our greedier algorithm
        """
        partner_obj = self.env["res.partner"] # on récupère tous les partners
        for company_id in self._ids:
            partners = partner_obj.search([('company_id', 'child_of', company_id)]) #critère de selection : cette company est associée
            partners.geo_code_retry()
        self.write({'date_last_partner_localization': fields.Date.context_today(self)})

    @api.depends()
    def _compute_partners_localization_stats(self):
        """
        method to compute some stats to display on a company view.
        nb_geocoding_success: number of partner who were geocoded successfully
        nb_geocoding_success_retry: number of partner who were geocoded successfully, using greedier algorithm
        nb_geocoding_failure: number of partner we tried and failed geocoding, and who wern't manually localized
        nb_geocoding_failure_retry: number of partner we tried and failed geocoding with greedier algorithm, and who wern't manually localized
        nb_manually_localized_partners: number of partners who were manually localized
        nb_left_to_geocode: number of partners we din't try to geocode and who weren't manually localized
        """
        partner_obj = self.env["res.partner"] # on récupère tous les partners
        for company in self:
            partners = partner_obj.search([('company_id', 'child_of', company.id)]) #critère de selection : cette company est associée
            nb_geocoding_success = partner_obj.search([('company_id', 'child_of', company.id),('id', 'in', partners._ids),('geocoding', '=', 'success')], count=True)
            nb_geocoding_success_retry = partner_obj.search([('company_id', 'child_of', company.id),('id', 'in', partners._ids),('geocoding', '=', 'success_retry')], count=True)
            nb_manually_localized_partners = partner_obj.search([('company_id', 'child_of', company.id),('id', 'in', partners._ids),('geocoding', '=', 'manual')], count=True)
            nb_geocoding_failure = partner_obj.search([('company_id', 'child_of', company.id),('id', 'in', partners._ids),('geocoding','=','failure')], count=True)
            nb_geocoding_failure_retry = partner_obj.search([('company_id', 'child_of', company.id),('id', 'in', partners._ids),('geocoding','=','failure_retry')], count=True)

            company.nb_partners = len(partners)
            company.nb_geocoding_success = nb_geocoding_success
            company.nb_geocoding_success_retry = nb_geocoding_success_retry
            company.nb_manually_localized_partners =  nb_manually_localized_partners
            company.nb_geocoding_failure = nb_geocoding_failure
            company.nb_geocoding_failure_retry = nb_geocoding_failure_retry
            company.nb_left_to_geocode = len(partners) - nb_geocoding_success - nb_geocoding_success_retry - nb_manually_localized_partners - nb_geocoding_failure - nb_geocoding_failure_retry

    @api.multi
    def geo_code(self):
        """
        Method to geocode a company's address using Nominatim.
        Will not try to geocode if GPS coordinates were manually set.
        """
        for company in self:
            if company.geocoding not in ('success','manual') and (company.geo_lat != 0 or company.geo_lng != 0):
                """
                if geocoding not in ('success','manual') and the company already has GPS coordinates
                    -> they were set outside of this module (before installation of the module for example)
                    therefore we try geocoding the address and set geocoding to 'manual' if geocoding fails
                """
                company._compute_nominatim_url()
                try:
                    result = json.load(urllib.urlopen(company.nominatim_input))
                except Exception as e:
                    raise UserError(_('Cannot contact geolocation servers. Please make sure that your Internet connection is up and running. (error: %s).') % e)

                if result == []:
                    company.write({
                        'date_last_localization': fields.Date.context_today(company),
                        'geocoding': 'manual',
                        'nominatim_response': "[]"
                    })
                else:
                    company.write({
                        'geocoding': 'success',
                        'geo_lat': result[0]['lat'],
                        'geo_lng': result[0]['lon'],
                        'date_last_localization': fields.Date.context_today(company),
                        'nominatim_response': json.dumps(result, indent=3, sort_keys=True, ensure_ascii = False)
                    })
            elif (not company.geocoding == 'manual'):
                company._compute_nominatim_url()
                try:
                    result = json.load(urllib.urlopen(company.nominatim_input))
                except Exception as e:
                    raise UserError(_('Cannot contact geolocation servers. Please make sure that your Internet connection is up and running (%s).') % e)

                if result == []:
                    company.write({
                        'geo_lat': 0,
                        'geo_lng': 0,
                        'date_last_localization': fields.Date.context_today(company),
                        'geocoding': 'failure',
                    })
                else:
                    company.write({
                        'geocoding': 'success',
                        'geo_lat': result[0]['lat'],
                        'geo_lng': result[0]['lon'],
                        'date_last_localization': fields.Date.context_today(company),
                    })
        return True

    @api.multi
    def action_view_geocoding_failure(self):
        self.ensure_one()
        partners = self.env['res.partner'].search([('company_id', 'child_of', self.id)])

        action = self.env.ref('of_geolocalize.action_partner_form_geocoding_failure').read()[0]

        if len(partners) > 1:
            action['domain'] = [('id', 'in', partners.ids)]
        elif len(partners) == 1:
            action['views'] = [(self.env.ref('base.view_partner_form').id, 'form')]
            action['res_id'] = partners.ids[0]
        else:
            action = {'type': 'ir.actions.act_window_close'}

        return action

    #will compute the lat and lng when a company is created if a searchable address is set
    @api.model
    def create(self, vals):
        company = super(ResCompany,self).create(vals)
        if (company.street or company.street2) and company.zip and company.city: 
            company.geo_code()
        return company

    #will recompute the lat and lng when a partner's address is modified
    @api.multi
    def write(self, vals):
        super(ResCompany,self).write(vals)
        if len(self._ids) == 1:
            if self.geocoding != 'manual':
                for key in vals:
                    if key in ('street', 'street2', 'city', 'state_id', 'country_id', 'zip'):
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
            })

