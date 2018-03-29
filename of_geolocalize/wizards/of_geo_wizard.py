# -*- coding: utf-8 -*-

# Requires a nominatim server up and running (for OpenFire geocoder)
# Requires request and googlemaps python packages (for Google Maps geocoder)

try:
    import json
except ImportError:
    json = None

try:
    import urllib
except ImportError:
    urllib = None

try:
    import requests
except ImportError:
    requests = None

try:
    import googlemaps
except ImportError:
    googlemaps = None

from odoo import api, fields, models
from odoo.exceptions import UserError
# import logging
# _logger = logging.getLogger(__name__)
from difflib import SequenceMatcher


class OFGeoWizard(models.TransientModel):
    _name = "of.geo.wizard"
    _description = u"Géocodage des partenaires sélectionnés"

    @api.model
    def _get_partner_ids(self):
        model = self._context['active_model']
        obj = self.env[model].browse(self._context.get('active_ids', []))
        if model == 'res.partner':
            partners = obj
        elif model == 'res.company':
            partners = obj.mapped('partner_id')
        else:
            raise UserError(u"Impossible de lancer cet outil depuis l'objet %s" % model)
        return partners

    @api.model
    def _get_config_stats(self):
        res_show_stats = self.env['ir.config_parameter'].get_param('show_stats')
        return res_show_stats

    # Stats
    nb_partners = fields.Integer(string=u'Nb partenaires', compute='_compute_global_geo_stats', readonly=True)
    nb_geocoding_success_openfire = fields.Integer(string=u'Geolocalisés avec OpenFire', compute='_compute_global_geo_stats', readonly=True)
    nb_geocoding_success_osm = fields.Integer(string=u'Geolocalisés avec OpenStreetMap', compute='_compute_global_geo_stats', readonly=True)
    nb_geocoding_success_ban = fields.Integer(string=u'Geolocalisés avec BANO', compute='_compute_global_geo_stats', readonly=True)
    nb_geocoding_success_google = fields.Integer(string=u'Geolocalisés avec Google Maps', compute='_compute_global_geo_stats', readonly=True)
    nb_geocoding_manually = fields.Integer(string=u'Geolocalisés manuellement', compute='_compute_global_geo_stats', readonly=True)
    nb_geocoding_total_success = fields.Integer(string=u'Total geolocalisés', compute='_compute_global_geo_stats', readonly=True)
    nb_geocoding_failure = fields.Integer(string=u'Échec du géocodage', compute='_compute_global_geo_stats', readonly=True)
    nb_no_address = fields.Integer(string=u"Sans adresse", compute='_compute_global_geo_stats', readonly=True)
    nb_geocoding_not = fields.Integer(string=u'Non géolocalisés', compute='_compute_global_geo_stats', readonly=True)

    por_success_openfire = fields.Float(digits=(3, 1), compute='_compute_global_geo_stats', readonly=True)
    por_success_osm = fields.Float(digits=(3, 1), compute='_compute_global_geo_stats', readonly=True)
    por_success_ban = fields.Float(digits=(3, 1), compute='_compute_global_geo_stats', readonly=True)
    por_success_google = fields.Float(digits=(3, 1), compute='_compute_global_geo_stats', readonly=True)
    por_manually = fields.Float(digits=(3, 1), compute='_compute_global_geo_stats', readonly=True)
    por_total_success = fields.Float(digits=(3, 1), compute='_compute_global_geo_stats', readonly=True)
    por_failure = fields.Float(digits=(3, 1), compute='_compute_global_geo_stats', readonly=True)
    por_no_address = fields.Float(digits=(3, 1), compute='_compute_global_geo_stats', readonly=True)
    por_not = fields.Float(digits=(3, 1), compute='_compute_global_geo_stats', readonly=True)

    show_stats_wizard = fields.Boolean(string=u"Montrer statistiques", default=_get_config_stats)

    # Stats géocodeurs
    openfire_try = 0
    openfire_success = 0
    openfire_fail = 0

    osm_try = 0
    osm_success = 0
    osm_fail = 0

    ban_try = 0
    ban_success = 0
    ban_fail = 0

    google_try = 0
    google_success = 0  #(web and API queries)
    google_fail = 0

    # Get taux success from last record in the of.geo.wizard
    @api.model
    def _get_taux_success_openfire(self):
        try:
            last_record = self.env['of.geo.wizard'].search([])[-1]
            taux_success_openfire = last_record.taux_success_openfire
        except:
            taux_success_openfire = ""
        return taux_success_openfire

    @api.model
    def _get_taux_success_osm(self):
        try: 
            last_record = self.env['of.geo.wizard'].search([])[-1]
            taux_success_osm = last_record.taux_success_osm
        except:
            taux_success_osm = ""
        return taux_success_osm

    @api.model
    def _get_taux_success_ban(self): 
        try:
            last_record = self.env['of.geo.wizard'].search([])[-1]
            taux_success_ban = last_record.taux_success_ban
        except:
            taux_success_ban = ""
        return taux_success_ban

    @api.model
    def _get_taux_success_google(self):  # from last record in the of.geo.wizard 
        try:
            last_record = self.env['of.geo.wizard'].search([])[-1]
            taux_success_google = last_record.taux_success_google
        except:
            taux_success_google = ""
        return taux_success_google

    taux_success_openfire = fields.Float(default=_get_taux_success_openfire, digits=(3, 1), readonly=True)
    taux_success_osm = fields.Float(default=_get_taux_success_osm, digits=(3, 1), readonly=True)
    taux_success_ban = fields.Float(default=_get_taux_success_ban, digits=(3, 1), readonly=True)
    taux_success_google = fields.Float(default=_get_taux_success_google, digits=(3, 1), readonly=True)

    # Config parameters
    # Géocodeurs
    use_nominatim_openfire = fields.Boolean(string=u"OpenFire")
    use_nominatim_osm = fields.Boolean(string=u"OpenStreetMap (OSM)")
    use_bano = fields.Boolean(string=u"Base d'adresses nationale ouverte (BANO)")
    use_google = fields.Boolean(string=u"Google maps")

    # Options
    best_precision = fields.Boolean(string=u"Choisir la meilleure précision des géocodeurs sélectionnés (lente)", default=False)

    # Traitement de données déjà géolocalisées
    overwrite_geoloc_all = fields.Boolean(string=u"Écraser tous ceux sélectionnés", default=False)
    overwrite_geoloc_except_manual = fields.Boolean(string=u"Écraser tous ceux sélectionnés sauf ceux geolocalisés manuellement", default=False)

    # Selected Partners
    partner_ids = fields.Many2many('res.partner', string=u"Partenaires sélectionnés", default=_get_partner_ids)

    nb_selected_partners = fields.Integer(string=u'Nb partenaires sélectionnés', compute='_compute_selected_stats', readonly=True)
    nb_selected_partners_success = fields.Integer(string=u'Nb partenaires sélectionnés reussi', compute='_compute_selected_stats', readonly=True)
    nb_selected_partners_failure = fields.Integer(string=u'Nb partenaires sélectionnés echoue', compute='_compute_selected_stats', readonly=True)
    nb_selected_partners_no_address = fields.Integer(string=u"Nb partenaires sélectionnés pas d'adresse", compute='_compute_selected_stats', readonly=True)
    nb_selected_partners_not = fields.Integer(string=u'Nb partenaires sélectionnés pas tentés', compute='_compute_selected_stats', readonly=True)
    nb_selected_partners_manual = fields.Integer(string=u'Nb partenaires sélectionnés manuel', compute='_compute_selected_stats', readonly=True)
    nb_selected_partners_to_geoloc = fields.Integer(string=u'Nb partenaires sélectionnés à géolocaliser', compute='_compute_selected_stats', readonly=True)

    @api.onchange('partner_ids', 'overwrite_geoloc_all', 'overwrite_geoloc_except_manual')
    def _compute_selected_stats(self):
        nb_selected_partners = len(self.partner_ids)
        nb_selected_partners_success = len([partner for partner in self.partner_ids if partner.geocoding == 'success_openfire' or partner.geocoding == 'success_osm' or partner.geocoding == 'success_bano' or partner.geocoding == 'success_google' or partner.geocoding == 'manual'])
        nb_selected_partners_failure = len([partner for partner in self.partner_ids if partner.geocoding == 'failure'])
        nb_selected_partners_no_address = len([partner for partner in self.partner_ids if partner.geocoding == 'no_address'])
        nb_selected_partners_manual = len([partner for partner in self.partner_ids if partner.geocoding == 'manual'])
        nb_selected_partners_not = len([partner for partner in self.partner_ids if partner.geocoding == 'not_tried'])

        self.nb_selected_partners = nb_selected_partners
        self.nb_selected_partners_success = nb_selected_partners_success
        self.nb_selected_partners_failure = nb_selected_partners_failure
        self.nb_selected_partners_no_address = nb_selected_partners_no_address
        self.nb_selected_partners_manual = nb_selected_partners_manual
        self.nb_selected_partners_not = nb_selected_partners_not
        
        if self.overwrite_geoloc_all:
            self.nb_selected_partners_to_geoloc = nb_selected_partners - nb_selected_partners_no_address
        elif self.overwrite_geoloc_all and self.overwrite_geoloc_except_manual:
            self.nb_selected_partners_to_geoloc = nb_selected_partners - nb_selected_partners_no_address
        elif self.overwrite_geoloc_except_manual:
            self.nb_selected_partners_to_geoloc = nb_selected_partners - nb_selected_partners_no_address - nb_selected_partners_manual
        else:
            self.nb_selected_partners_to_geoloc = nb_selected_partners - nb_selected_partners_no_address - nb_selected_partners_success

    @api.depends('partner_ids')
    def _compute_global_geo_stats(self):
        partner_obj = self.env["res.partner"]
        partners = partner_obj.search([])

        # Get
        nb_partners = len(partners)
        nb_geocoding_success_openfire = partner_obj.search([('geocoding', '=', 'success_openfire')], count=True)
        nb_geocoding_success_osm = partner_obj.search([('geocoding', '=', 'success_osm')], count=True)
        nb_geocoding_success_ban = partner_obj.search([('geocoding', '=', 'success_bano')], count=True)
        nb_geocoding_success_google = partner_obj.search([('geocoding', '=', 'success_google')], count=True)
        nb_geocoding_manually = partner_obj.search([('geocoding', '=', 'manual')], count=True)
        nb_geocoding_failure = partner_obj.search([('geocoding', '=', 'failure')], count=True)
        nb_no_address = partner_obj.search([('geocoding', '=', 'no_address')], count=True)
        nb_geocoding_not = partner_obj.search([('geocoding', '=', 'not_tried')], count=True)

        # Calcule
        nb_geocoding_total_success = nb_geocoding_success_openfire + nb_geocoding_success_osm + nb_geocoding_success_ban + nb_geocoding_success_google + nb_geocoding_manually
        por_success_openfire = float(nb_geocoding_success_openfire) / float(nb_partners) * 100
        por_success_osm = float(nb_geocoding_success_osm) / float(nb_partners) * 100
        por_success_ban = float(nb_geocoding_success_ban) / float(nb_partners) * 100
        por_success_google = float(nb_geocoding_success_google) / float(nb_partners) * 100
        por_manually = float(nb_geocoding_manually) / float(nb_partners) * 100
        por_total_success = float(nb_geocoding_total_success) / float(nb_partners) * 100
        por_failure = float(nb_geocoding_failure) / float(nb_partners) * 100
        por_no_address = float(nb_no_address) / float(nb_partners) * 100
        por_not = float(nb_geocoding_not) / float(nb_partners) * 100

        # Return
        self.nb_partners = nb_partners
        self.nb_geocoding_success_openfire = nb_geocoding_success_openfire
        self.nb_geocoding_success_osm = nb_geocoding_success_osm
        self.nb_geocoding_success_ban = nb_geocoding_success_ban
        self.nb_geocoding_success_google = nb_geocoding_success_google
        self.nb_geocoding_manually = nb_geocoding_manually
        self.nb_geocoding_total_success = nb_geocoding_total_success
        self.nb_geocoding_failure = nb_geocoding_failure
        self.nb_no_address = nb_no_address
        self.nb_geocoding_not = nb_geocoding_not

        self.por_success_openfire = por_success_openfire
        self.por_success_osm = por_success_osm
        self.por_success_ban = por_success_ban
        self.por_success_google = por_success_google
        self.por_manually = por_manually
        self.por_total_success = por_total_success
        self.por_failure = por_failure
        self.por_no_address = por_no_address
        self.por_not = por_not

    # Funcion to check string similarity [difflib]
    def similar(self, a, b):
        return SequenceMatcher(None, a, b).ratio()

    # GEOCODERS
    # Geocoding with OPENFIRE
    def geo_openfire(self, partner):
        # Variables
        geocoding = ""
        geocodeur = 'nominatim_openfire'
        latitud = ""
        longitud = ""
        precision = ""

        # Start
        API_URL = self.env['ir.config_parameter'].get_param('url_openfire').strip()

        # Test geocoder URL
        if self.use_nominatim_openfire == True and API_URL == False:
            raise UserError(u"L'URL du géocodeur OpenFire n'est pas configurée. Vérifiez votre paramétrage ou désactivez ce géocodeur")
        if API_URL.startswith('https://') or API_URL.startswith('http://'):
            pass
        else:
            raise UserError((u"L'URL du géocodeur OpenFire ne semble pas correcte: %s. Vérifiez votre paramétrage ou désactivez ce géocodeur") % API_URL)

        # Get address data
        query = partner.get_addr_params()

        if not query:
            geocoding = 'no_address'
            geocodeur = ""
            latitud = 0
            longitud = 0
            precision = 'no_address'
        else:
            query = urllib.quote_plus(query.strip().encode('utf8'))
            full_query = API_URL + query + '&format=json'

            # Server query and response
            try:
                req = requests.get(full_query)
                res = req.json()
                self.openfire_try += 1
            except Exception as e:
                raise UserError((u"Impossible de contacter le serveur de géolocalisation. Assurez-vous que votre connexion internet est opérationnelle et que l'URL est définie (%s)") % e)

            if not res:
                self.openfire_fail += 1
                geocoding = 'failure'
                latitud = 0
                longitud = 0
                precision = "unknown"
            else:
                try:
                    longitud = res[0]['lon']
                except:
                    longitud = ""
                try:
                    latitud = res[0]['lat']
                except:
                    latitud = ""
                try:
                    osm_type = res[0]['osm_type']
                except:
                    osm_type = "unknown"

                # Determine precision
                if osm_type == "way" or osm_type == "node":
                    precision = "high"
                elif osm_type == "relation":
                    precision = "medium"
                elif osm_type == "unknown":
                    precision = "low"
                else:
                    precision = "unknown"

                # Discriminate false positives
                if precision == 'high':
                    # Simplify response address
                    res_address = res[0]['display_name']
                    fields = res_address.split(",")
                    res_street = fields[0]
                    res_zip = fields[-2]
                    res_city = fields[3]
                    reformed_res_address = res_street + res_zip + res_city
                    reformed_res_address = reformed_res_address.upper()
                    # Simplify query address
                    reformed_query_address = query.upper()
                    has_country = reformed_query_address.split(' ')[-1]
                    if has_country == "FRANCE":
                        reformed_query_address = ' '.join(reformed_query_address.split(' ')[:-1])
                    # Compare
                    ratio = self.similar(reformed_query_address, reformed_res_address)

                    if ratio < 0.6:
                        precision = "low"
                        # Detect different zip (mark as failure if dif)
                        if partner.zip:
                            res_zip = fields[-2]
                            zip_ratio = self.similar(partner.zip,res_zip)
                            if zip_ratio < 0.9:
                                precision = ""
                    elif ratio < 0.7:
                        precision = "medium"

                if longitud and latitud and precision:
                    self.openfire_success += 1
                    geocoding = 'success_openfire'
                    latitud = latitud
                    longitud = longitud
                    precision = precision
                else:
                    self.openfire_fail += 1
                    geocoding = 'failure'
                    latitud = 0
                    longitud = 0
                    precision = "unknown"

        # _logger.info("RESULTS OPENFIRE == geocoding= %s , geocodeur= %s, latitud= %s, longitud= %s  , precision= %s", geocoding,geocodeur,latitud,longitud,precision)
        return geocoding,geocodeur,latitud,longitud,precision

    # Géocodage avec OSM
    def geo_osm(self, partner):
        # Variables
        geocoding = ""
        geocodeur = 'nominatim_osm'
        latitud = ""
        longitud = ""
        precision = ""

        # Start
        API_URL = partner.env['ir.config_parameter'].get_param('url_osm')

        # Teste URL géocodage
        if self.use_nominatim_osm == True and API_URL == False:
            raise UserError(u"L'URL du géocodeur OpenStreetMap n'est pas configurée. Vérifiez votre paramétrage ou désactivez ce géocodeur")
        if API_URL.startswith('https://') or API_URL.startswith('http://'):
            pass
        else:
            raise UserError((u"L'URL du géocodeur OpenStreetMap ne semble pas correcte: %s. Vérifiez votre paramétrage ou désactivez ce géocodeur") % API_URL)

        # Get address data
        query = partner.get_addr_params()

        if not query:
            geocoding = 'no_address'
            geocodeur = ""
            latitud = 0
            longitud = 0
            precision = 'no_address'
        else:
            query_send = urllib.quote_plus(query.strip().encode('utf8'))
            full_query = API_URL + query_send + '&format=json'

            # Server query and response
            try:
                req = requests.get(full_query)
                res = req.json()
                self.osm_try += 1
            except Exception as e:
                raise UserError((u"Impossible de contacter le serveur de géolocalisation. Assurez-vous que votre connexion Internet est opérationnelle et que l'URL est définie (%s)") % e)

            if not res:
                self.osm_fail += 1
                geocoding = 'failure'
                latitud = 0
                longitud = 0
                precision = "unknown"
            else:
                try:
                    longitud = res[0]['lon']
                except:
                    longitud = ""
                try:
                    latitud = res[0]['lat']
                except:
                    latitud = ""
                try:
                    osm_type = res[0]['osm_type']
                except:
                    osm_type = "unknown"

                # Determine precision
                if osm_type == "way" or osm_type == "node":
                    precision = "high"
                elif osm_type == "relation":
                    precision = "medium"
                elif osm_type == "unknown":
                    precision = "low"
                else:
                    precision = "unknown"

                # Discriminate false positives
                if precision == 'high':
                    # Simplify response address
                    res_address = res[0]['display_name']
                    fields = res_address.split(",")
                    res_street = fields[0]
                    res_zip = fields[-2]
                    res_city = fields[3]
                    reformed_res_address = res_street + res_zip + res_city
                    reformed_res_address = reformed_res_address.upper()
                    # Simplify query address
                    reformed_query_address = query.upper()
                    has_country = reformed_query_address.split(' ')[-1]
                    if has_country == "FRANCE":
                        reformed_query_address = ' '.join(reformed_query_address.split(' ')[:-1])
                    # Compare
                    ratio = self.similar(reformed_query_address, reformed_res_address)

                    if ratio < 0.6:
                        precision = "low"
                        # Detect different zip (mark as failure if dif)
                        if partner.zip:
                            res_zip = fields[-2]
                            zip_ratio = self.similar(partner.zip,res_zip)
                            if zip_ratio < 0.9:
                                precision = ""
                    elif ratio < 0.7:
                        precision = "medium"

                if longitud and latitud and precision:
                    self.osm_success += 1
                    geocoding = 'success_osm'
                    latitud = latitud
                    longitud = longitud
                    precision = precision
                else:
                    self.osm_fail += 1
                    geocoding = 'failure'
                    latitud = 0
                    longitud = 0
                    precision = "unknown"

        # _logger.info("RESULTS OSM == geocoding= %s , geocodeur= %s, latitud= %s, longitud= %s  , precision= %s", geocoding,geocodeur,latitud,longitud,precision)
        return geocoding,geocodeur,latitud,longitud,precision

    # Geocoding with BANO
    def geo_ban(self, partner):
        # Variables
        geocoding = ""
        geocodeur = 'bano'
        latitud = ""
        longitud = ""
        precision = ""

        # Start
        API_URL = partner.env['ir.config_parameter'].get_param('url_bano').strip()

        # Test geocoder URL
        if self.use_bano == True and API_URL == False:
            raise UserError(u"L'URL du géocodeur BANO n'est pas configurée. Vérifiez votre paramétrage ou désactivez ce géocodeur")
        if API_URL.startswith('https://') or API_URL.startswith('http://'):
            pass
        else:
            raise UserError((u"L'URL du géocodeur BANO ne semble pas correcte: %s. Vérifiez votre paramétrage ou désactivez ce géocodeur") % API_URL)

        # Get address data
        query = partner.get_addr_params()

        if not query:
            geocoding = 'no_address'
            geocodeur = ""
            latitud = 0
            longitud = 0
            precision = 'no_address'
        else:
            params = {
                'q': query,
                'limit': '2',
                'autocomplete': '1',
            }

            # Server query and response
            try:
                req = requests.get(API_URL, params=params)
                res = req.json()
                self.ban_try += 1
            except Exception as e:
                raise UserError((u"Impossible de contacter le serveur de géolocalisation. Assurez-vous que votre connexion Internet est opérationnelle et que l'URL est définie (%s)") % e)

            if not res:
                self.ban_fail += 1
                geocoding = 'fail_ban'
                latitud = 0
                longitud = 0
                precision = "unknown"
            else:
                try:
                    results = res['features'][0]
                    latitud = results['geometry']['coordinates'][1]
                    longitud = results['geometry']['coordinates'][0]
                except:
                    results = ""
                    latitud = ""
                    longitud = ""

                if results:
                    # Determine precision
                    try:
                        response_street = results['properties']['street'].upper().strip()
                        response_street = filter(lambda c: not c.isdigit(), response_street)
                    except:
                        response_street = ""
                    try:
                        response_zip = results['properties']['postcode'].strip()
                    except:
                        response_zip = ""
                    try:
                        response_city = results['properties']['city'].upper().strip()
                    except:
                        response_city = ""

                    if response_street:
                        precision = "high"
                    elif response_city or response_zip:
                        precision = "medium"
                    else:
                        precision = "low"

                    # Discriminate false positives
                    if precision == "high":
                        # Simplify query street
                        if partner.street_query:
                            reformed_query_street = partner.street_query.upper().strip()
                        else:
                            reformed_query_street = ""

                        # Compare
                        ratio_street = self.similar(reformed_query_street, response_street)

                        if ratio_street < 0.6:
                            precision = "low"
                            # Detect different zip (mark as failure if dif)
                            if partner.zip:
                                query_zip = partner.zip.strip()
                                zip_ratio = self.similar(query_zip,response_zip)
                                if zip_ratio < 0.9:
                                    precision = ""
                                    
                        elif ratio_street < 0.7:
                            precision = "medium"
                            if partner.zip:
                                query_zip = partner.zip.strip()
                                zip_ratio = self.similar(query_zip,response_zip)
                                if zip_ratio < 0.9:
                                    precision = ""

                    if precision == "medium":
                        # Check zip
                        if partner.zip:
                            query_zip = partner.zip.strip()
                            zip_ratio = self.similar(query_zip,response_zip)
                            if zip_ratio < 0.9:
                                precision = ""
                        # Check city        
                        if partner.city:
                            query_city = partner.city.strip().upper()
                            city_ratio = self.similar(query_city,response_city)
                            if city_ratio < 0.6:
                                precision = ""

                if longitud and latitud and precision:
                    self.ban_success += 1
                    geocoding = 'success_bano'
                    latitud = latitud
                    longitud = longitud
                    precision = precision
                else:
                    self.ban_fail += 1
                    geocoding = 'failure'
                    latitud = 0
                    longitud = 0
                    precision = "unknown"

        # _logger.info("RESULTS BAN == geocoding= %s , geocodeur= %s, latitud= %s, longitud= %s  , precision= %s", geocoding,geocodeur,latitud,longitud,precision)
        return geocoding,geocodeur,latitud,longitud,precision

    def geo_google(self, partner):
        # Variables
        geocoding = ""
        geocodeur = 'google_maps'
        latitud = ""
        longitud = ""
        precision = ""

        # Start
        # Get Google API URL
        API_URL = partner.env['ir.config_parameter'].get_param('url_google').strip()

        # Test geocoder URL
        if self.use_google == True and API_URL == False:
            raise UserError(u"L'URL du géocodeur Google Maps n'est pas configurée. Vérifiez votre paramétrage ou désactivez ce géocodeur")
        if API_URL.startswith('https://') or API_URL.startswith('http://'):
            pass
        else:
            raise UserError((u"L'URL du géocodeur Google Maps ne semble pas correcte: %s. Vérifiez votre paramétrage ou désactivez ce géocodeur") % API_URL)

        # Get address data
        query = partner.get_addr_params()
        using_api = ""

        if not query:
            geocoding = 'no_address'
            geocodeur = ""
            latitud = 0
            longitud = 0
            precision = 'no_address'
        else:
            params = {
                'address': query,
                'sensor': 'false',
            }

            # Server query and response
            try:
                req = requests.get(API_URL, params=params)
                res = req.json()
                self.google_try += 1
            except Exception as e:
                raise UserError((u"Impossible de contacter le serveur de géolocalisation. Assurez-vous que votre connexion Internet est opérationnelle et que l'URL est définie (%s)") % e)

            if not res:
                self.google_fail += 1
                geocoding = 'failure'
                latitud = 0
                longitud = 0
                precision = "unknown"
            else:
                if res['status'] == "ZERO_RESULTS":
                    self.google_fail += 1
                    geocoding = 'failure'
                    latitud = 0
                    longitud = 0
                    precision = "unknown"
                elif res['status'] == "OK":
                    using_api = "no"
                    results = res['results'][0]

                    try:
                        geometry = results['geometry']
                    except:
                        geometry = ""

                    try:
                        postcodes = results['postcode_localities']
                    except:
                        postcodes = ""

                    try:
                        partial_match = results['partial_match']
                    except:
                        partial_match = ""

                    if partial_match and not postcodes:
                        precision = "low"
                    elif partial_match and postcodes:
                        precision = "medium"
                    elif partial_match:
                        precision = "low"
                    elif geometry:
                        precision = "high"

                    if precision == "high":
                        if results['geometry']['location_type'] == "ROOFTOP" \
                        or results['geometry']['location_type'] == "RANGE_INTERPOLATED":

                            # Simplify response address
                            response_address = results['formatted_address'].replace(',', '').upper().strip()
                            # Simplify query address
                            query_address = query.upper()
                            # Compare
                            ratio = self.similar(query_address, response_address)

                            if ratio > 0.9:
                                precision = "high"
                            elif ratio > 0.8:
                                precision = "medium"
                            elif ratio > 0.7:
                                precision = "low"
                            else:
                                precision = "unknown"

                            latitud = results['geometry']['location']['lat']
                            longitud = results['geometry']['location']['lng']

                        elif results['geometry']['location_type'] == "GEOMETRIC_CENTER" \
                        or results['geometry']['location_type'] == "APPROXIMATE":
                            latitud = results['geometry']['location']['lat']
                            longitud = results['geometry']['location']['lng']
                            precision = "medium"

                    elif precision == "medium":
                        # TODO : Test city and zip by comparing
                        latitud = results['geometry']['location']['lat']
                        longitud = results['geometry']['location']['lng']

                    elif precision == "low":
                        latitud = results['geometry']['location']['lat']
                        longitud = results['geometry']['location']['lng']

                    # Results
                    if longitud and latitud and precision:
                        self.google_success += 1
                        geocoding = 'success_google'
                        latitud = latitud
                        longitud = longitud
                        precision = precision
                    else:
                        self.google_fail += 1
                        geocoding = 'failure'
                        latitud = 0
                        longitud = 0
                        precision = "unknown"

                elif res['status'] == "OVER_QUERY_LIMIT":
                    using_api = "yes"

                    # Get Google API key
                    google_api_key = partner.env['ir.config_parameter'].get_param('google_api_key')

                    # Server query and response
                    gmaps = googlemaps.Client(key=google_api_key)
                    self.google_try += 1

                    try:
                        res = gmaps.geocode(query)
                        results = res[0]

                        try:
                            geometry = results['geometry']
                        except:
                            geometry = ""

                        try:
                            postcodes = results['postcode_localities']
                        except:
                            postcodes = ""

                        try:
                            partial_match = results['partial_match']
                        except:
                            partial_match = ""

                        if partial_match and not postcodes:
                            precision = "low"
                        elif partial_match and postcodes:
                            precision = "medium"
                        elif partial_match:
                            precision = "low"
                        elif geometry:
                            precision = "high"

                        if precision == "high":

                            if results['geometry']['location_type'] == "ROOFTOP" \
                            or results['geometry']['location_type'] == "RANGE_INTERPOLATED":

                                # Simplify response address
                                response_address = results['formatted_address'].replace(',', '').upper().strip()
                                # Simplify query address
                                query_address = query.upper()
                                # Compare
                                ratio = self.similar(query_address, response_address)

                                if ratio > 0.9:
                                    precision = "high"
                                elif ratio > 0.8:
                                    precision = "medium"
                                elif ratio > 0.7:
                                    precision = "low"
                                else:
                                    precision = "unknown"

                                latitud = results['geometry']['location']['lat']
                                longitud = results['geometry']['location']['lng']

                            elif results['geometry']['location_type'] == "GEOMETRIC_CENTER" \
                            or results['geometry']['location_type'] == "APPROXIMATE":
                                latitud = results['geometry']['location']['lat']
                                longitud = results['geometry']['location']['lng']
                                precision = "medium"

                        elif precision == "medium":
                            # TODO : Test city and zip by comparing
                            latitud = results['geometry']['location']['lat']
                            longitud = results['geometry']['location']['lng']

                        elif precision == "low":
                            latitud = results['geometry']['location']['lat']
                            longitud = results['geometry']['location']['lng']

                        # Results
                        if longitud and latitud and precision:
                            self.google_success += 1
                            geocoding = 'success_google'
                            latitud = latitud
                            longitud = longitud
                            precision = precision
                        else:
                            self.google_fail += 1
                            geocoding = 'failure'
                            latitud = 0
                            longitud = 0
                            precision = "unknown"
                    except: # No results API
                        # _logger.info("GOOGLE API ERROR [If you see this message for all API queries your our key is not valid]")
                        self.google_fail += 1
                        geocoding = 'failure'
                        latitud = 0
                        longitud = 0
                        precision = "unknown"
                elif res['status'] == "REQUEST_DENIED" or res['status'] == "INVALID_REQUEST" or res['status'] == "UNKNOWN_ERROR":
                    self.google_fail += 1
                    geocoding = 'failure'
                    latitud = 0
                    longitud = 0
                    precision = "unknown"
                else:
                    self.google_fail += 1
                    geocoding = 'failure'
                    latitud = 0
                    longitud = 0
                    precision = "unknown"

        # if using_api == "yes":
        #     _logger.info("RESULTS API GOOGLE == geocoding= %s , geocodeur= %s, latitud= %s, longitud= %s  , precision= %s", geocoding,geocodeur,latitud,longitud,precision)
        # elif using_api == "no":
        #     _logger.info("RESULTS WEB GOOGLE == geocoding= %s , geocodeur= %s, latitud= %s, longitud= %s  , precision= %s", geocoding,geocodeur,latitud,longitud,precision)
        # else:
        #     _logger.info("RESULTS GOOGLE == geocoding= %s , geocodeur= %s, latitud= %s, longitud= %s  , precision= %s", geocoding,geocodeur,latitud,longitud,precision)
        return geocoding,geocodeur,latitud,longitud,precision

    # Erase button
    @api.multi
    def action_reset_geo_val_selected(self):
        # _logger.info("OVERRIDING GEOCODING DATA")
        for partner in self.partner_ids:
            if not partner.geocoding == 'manual': # Protect manual geocoding
                partner.write({
                    'geocoding': 'not_tried',
                    'geocodeur': 'unknown',
                    'geo_lat': 0,
                    'geo_lng': 0,
                    'precision': 'not_tried',
                    'date_last_localization': fields.Datetime.context_timestamp(self, fields.datetime.now()),
                    'geocoding_response': u"Réinitialisé",
                })
        return { "type": "ir.actions.do_nothing", }

    # INDIVIDUAL GEOCODING
    def action_button_geo_openfire(self):
        partner_id = self._context.get('active_id')
        if not partner_id:
            raise UserError(u"Un partenaire doit être fourni")
        partner = self.env['res.partner'].browse(partner_id)

        # Test geocoder URL
        API_URL = partner.env['ir.config_parameter'].get_param('url_openfire')
        if API_URL == False:
            raise UserError(u"L'URL du géocodeur OpenFire n'est pas configurée. Vérifiez votre paramétrage ou utilisez un autre géocodeur")
        if API_URL.startswith('https://') or API_URL.startswith('http://'):
            pass
        else:
            raise UserError((u"L'URL du géocodeur OpenFire ne semble pas correcte: %s. Vérifiez votre paramétrage ou utilisez un autre géocodeur") % API_URL)

        results = self.geo_openfire(partner)
        partner.write({
            'geocoding': results[0],
            'geocodeur': results[1],
            'geo_lat': results[2],
            'geo_lng': results[3],
            'precision': results[4],
            'date_last_localization': fields.Datetime.context_timestamp(self, fields.datetime.now()),
            'geocoding_response': json.dumps(results, indent=3, sort_keys=True, ensure_ascii=False),
        })
        return True

    def action_button_geo_osm(self):
        partner_id = self._context.get('active_id')
        if not partner_id:
            raise UserError(u"Un partenaire doit être fourni")
        partner = self.env['res.partner'].browse(partner_id)

        # Test geocoder URL
        API_URL = partner.env['ir.config_parameter'].get_param('url_osm')
        if API_URL == False:
            raise UserError(u"L'URL du géocodeur OpenStreetMap n'est pas configurée. Vérifiez votre paramétrage ou utilisez un autre géocodeur")
        if API_URL.startswith('https://') or API_URL.startswith('http://'):
            pass
        else:
            raise UserError((u"L'URL du géocodeur OpenStreetMap ne semble pas correcte: %s. Vérifiez votre paramétrage ou utilisez un autre géocodeur") % API_URL)

        results = self.geo_osm(partner)
        
        partner.write({
            'geocoding': results[0],
            'geocodeur': results[1],
            'geo_lat': results[2],
            'geo_lng': results[3],
            'precision': results[4],
            'date_last_localization': fields.Datetime.context_timestamp(self, fields.datetime.now()),
            'geocoding_response': json.dumps(results, indent=3, sort_keys=True, ensure_ascii=False),
        })
        return True

    def action_button_geo_ban(self):
        partner_id = self._context.get('active_id')
        if not partner_id:
            raise UserError(u"Un partenaire doit être fourni")
        partner = self.env['res.partner'].browse(partner_id)

        # Test geocoder URL
        API_URL = partner.env['ir.config_parameter'].get_param('url_bano')
        if API_URL == False:
            raise UserError(u"L'URL du géocodeur BANO n'est pas configurée. Vérifiez votre paramétrage ou utilisez un autre géocodeur")
        if API_URL.startswith('https://') or API_URL.startswith('http://'):
            pass
        else:
            raise UserError((u"L'URL du géocodeur BANO ne semble pas correcte: %s. Vérifiez votre paramétrage ou utilisez un autre géocodeur") % API_URL)

        results = self.geo_ban(partner)
        partner.write({
            'geocoding': results[0],
            'geocodeur': results[1],
            'geo_lat': results[2],
            'geo_lng': results[3],
            'precision': results[4],
            'date_last_localization': fields.Datetime.context_timestamp(self, fields.datetime.now()),
            'geocoding_response': json.dumps(results, indent=3, sort_keys=True, ensure_ascii=False),
        })
        return True

    def action_button_geo_google(self):
        partner_id = self._context.get('active_id')
        if not partner_id:
            raise UserError(u"Un partenaire doit être fourni")
        partner = self.env['res.partner'].browse(partner_id)

        # Test geocoder URL
        API_URL = partner.env['ir.config_parameter'].get_param('url_google')
        if API_URL == False:
            raise UserError(u"L'URL du géocodeur Google Maps n'est pas configurée. Vérifiez votre paramétrage ou utilisez un autre géocodeur")
        if API_URL.startswith('https://') or API_URL.startswith('http://'):
            pass
        else:
            raise UserError((u"L'URL du géocodeur Google Maps ne semble pas correcte: %s. Vérifiez votre paramétrage ou désactivez ce géocodeur") % API_URL)

        results = self.geo_google(partner)
        partner.write({
            'geocoding': results[0],
            'geocodeur': results[1],
            'geo_lat': results[2],
            'geo_lng': results[3],
            'precision': results[4],
            'date_last_localization': fields.Datetime.context_timestamp(self, fields.datetime.now()),
            'geocoding_response': json.dumps(results, indent=3, sort_keys=True, ensure_ascii=False),
        })
        return True

    def action_button_reset_geo_val(self):
        # Geocoding manual = False (Delete manual records too)
        if self.partner_ids.geocoding == 'manual':
            self.partner_ids.geocoding = "not_tried"
            
        self.action_reset_geo_val_selected()
        return True

    # GEOCODING BY LOT (Geolocalizer button)
    @api.multi
    def action_geocode(self):
        # _logger.info("START GEOCODING")

        # count writes, commit each 100 writes
        cmpt = 0

        # Check config errors
        # Test if at least one geocoder has been choosen
        if self.use_nominatim_openfire == False and self.use_nominatim_osm == False and self.use_bano == False and self.use_google == False:
            raise UserError(u"Vous devez choisir au moins un géocodeur.")

        # SECUENTIAL GEOCODING
        for use_geocoder, geocoder_function, geocoder_name in (
            (self.use_nominatim_openfire, self.geo_openfire, 'openfire'),
            (self.use_nominatim_osm, self.geo_osm, 'osm'),
            (self.use_bano, self.geo_ban, 'ban'),
            (self.use_google, self.geo_google, 'google'),
        ):
            if not use_geocoder:
                continue

            for partner in self.partner_ids:

                # Overwrite all best precision
                if self.overwrite_geoloc_all and self.best_precision:
                    results = geocoder_function(partner)
                    get_precision = results[4]
                    get_record_precision = partner.precision

                    if get_precision == "high":
                        get_precision = 3
                    elif get_precision == "medium":
                        get_precision = 2
                    elif get_precision == "low":
                        get_precision = 1
                    else:
                        get_precision = 0

                    if get_record_precision == "high":
                        get_record_precision = 3
                    elif get_record_precision == "medium":
                        get_record_precision = 2
                    elif get_precision == "low":
                        get_record_precision = 1
                    else:
                        get_record_precision = 0

                    if get_precision > get_record_precision:
                        partner.write({
                            'geocoding': results[0],
                            'geocodeur': results[1],
                            'geo_lat': results[2],
                            'geo_lng': results[3],
                            'precision': results[4],
                            'date_last_localization': fields.Datetime.context_timestamp(self, fields.datetime.now()),
                            'geocoding_response': json.dumps(results, indent=3, sort_keys=True, ensure_ascii=False),
                        })
                        cmpt += 1
                    elif get_precision == 0 and get_record_precision == 0:
                        partner.write({
                            'geocoding': results[0],
                            'geocodeur': results[1],
                            'geo_lat': results[2],
                            'geo_lng': results[3],
                            'precision': results[4],
                            'date_last_localization': fields.Datetime.context_timestamp(self, fields.datetime.now()),
                            'geocoding_response': json.dumps(results, indent=3, sort_keys=True, ensure_ascii=False),
                        })
                        cmpt += 1

                # Overwrite all except manual and best precision
                elif self.overwrite_geoloc_except_manual and self.best_precision:
                    if partner.geocoding not in ('manual'):
                        results = geocoder_function(partner)
                        get_precision = results[4]
                        get_record_precision = partner.precision

                        if get_precision == "high":
                            get_precision = 3
                        elif get_precision == "medium":
                            get_precision = 2
                        elif get_precision == "low":
                            get_precision = 1
                        else:
                            get_precision = 0

                        if get_record_precision == "high":
                            get_record_precision = 3
                        elif get_record_precision == "medium":
                            get_record_precision = 2
                        elif get_precision == "low":
                            get_record_precision = 1
                        else:
                            get_record_precision = 0

                        if get_precision > get_record_precision:
                            partner.write({
                                'geocoding': results[0],
                                'geocodeur': results[1],
                                'geo_lat': results[2],
                                'geo_lng': results[3],
                                'precision': results[4],
                                'date_last_localization': fields.Datetime.context_timestamp(self, fields.datetime.now()),
                                'geocoding_response': json.dumps(results, indent=3, sort_keys=True, ensure_ascii=False),
                            })
                            cmpt += 1
                        elif get_precision == 0 and get_record_precision == 0:
                            partner.write({
                                'geocoding': results[0],
                                'geocodeur': results[1],
                                'geo_lat': results[2],
                                'geo_lng': results[3],
                                'precision': results[4],
                                'date_last_localization': fields.Datetime.context_timestamp(self, fields.datetime.now()),
                                'geocoding_response': json.dumps(results, indent=3, sort_keys=True, ensure_ascii=False),
                            })
                            cmpt += 1

                # Not_tried no failure and best precision
                elif self.best_precision: 
                    if partner.geocoding not in ('success_openfire', 'success_osm', 'success_bano', 'success_google', 'manual', 'no_address'):
                        results = geocoder_function(partner)
                        get_precision = results[4]
                        get_record_precision = partner.precision

                        if get_precision == "high":
                            get_precision = 3
                        elif get_precision == "medium":
                            get_precision = 2
                        elif get_precision == "low":
                            get_precision = 1
                        else:
                            get_precision = 0

                        if get_record_precision == "high":
                            get_record_precision = 3
                        elif get_record_precision == "medium":
                            get_record_precision = 2
                        elif get_precision == "low":
                            get_record_precision = 1
                        else:
                            get_record_precision = 0

                        if get_precision > get_record_precision:
                            partner.write({
                                'geocoding': results[0],
                                'geocodeur': results[1],
                                'geo_lat': results[2],
                                'geo_lng': results[3],
                                'precision': results[4],
                                'date_last_localization': fields.Datetime.context_timestamp(self, fields.datetime.now()),
                                'geocoding_response': json.dumps(results, indent=3, sort_keys=True, ensure_ascii=False),
                            })
                            cmpt += 1
                        elif get_precision == 0 and get_record_precision == 0:
                            partner.write({
                                'geocoding': results[0],
                                'geocodeur': results[1],
                                'geo_lat': results[2],
                                'geo_lng': results[3],
                                'precision': results[4],
                                'date_last_localization': fields.Datetime.context_timestamp(self, fields.datetime.now()),
                                'geocoding_response': json.dumps(results, indent=3, sort_keys=True, ensure_ascii=False),
                            })
                            cmpt += 1

                # Overwrite all and not best precision
                elif self.overwrite_geoloc_all and not self.best_precision:
                    results = geocoder_function(partner)
                    partner.write({
                        'geocoding': results[0],
                        'geocodeur': results[1],
                        'geo_lat': results[2],
                        'geo_lng': results[3],
                        'precision': results[4],
                        'date_last_localization': fields.Datetime.context_timestamp(self, fields.datetime.now()),
                        'geocoding_response': json.dumps(results, indent=3, sort_keys=True, ensure_ascii=False),
                    })
                    cmpt += 1

                # Overwrite all except manual and not best precision
                elif self.overwrite_geoloc_except_manual and not self.best_precision:
                    if partner.geocoding not in ('manual'):
                        results = geocoder_function(partner)
                        partner.write({
                            'geocoding': results[0],
                            'geocodeur': results[1],
                            'geo_lat': results[2],
                            'geo_lng': results[3],
                            'precision': results[4],
                            'date_last_localization': fields.Datetime.context_timestamp(self, fields.datetime.now()),
                            'geocoding_response': json.dumps(results, indent=3, sort_keys=True, ensure_ascii=False),
                        })
                        cmpt += 1

                # Not_tried no failure and not best precision
                elif not self.best_precision:
                    if partner.geocoding not in ('success_openfire', 'success_osm', 'success_bano', 'success_google', 'manual', 'no_address'):
                        results = geocoder_function(partner)
                        partner.write({
                            'geocoding': results[0],
                            'geocodeur': results[1],
                            'geo_lat': results[2],
                            'geo_lng': results[3],
                            'precision': results[4],
                            'date_last_localization': fields.Datetime.context_timestamp(self, fields.datetime.now()),
                            'geocoding_response': json.dumps(results, indent=3, sort_keys=True, ensure_ascii=False),
                        })
                        cmpt += 1

            # Stats geocoders
            try:
                taux_success = float(getattr(self, '%s_success' % geocoder_name)) / float(getattr(self, '%s_try' % geocoder_name)) * 100
                taux_success = float("{0:.2f}".format(taux_success))
                self['taux_success_%s' % geocoder_name] = taux_success
                # _logger.info("taux_success_%s = %d", geocoder_name, taux_success)
            except:
                self['taux_success_%s' % geocoder_name] = ""
                # _logger.info("taux_sucess_%s = ERROR", geocoder_name)

            if cmpt % 100 == 0:
                # _logger.info("COMMIT TO DB of %d ENTRIES", cmpt)
                self._cr.commit()

        return { "type": "ir.actions.do_nothing", }
