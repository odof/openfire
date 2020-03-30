# -*- coding: utf-8 -*-

from odoo import api, fields, models, tools
from odoo.exceptions import UserError
from difflib import SequenceMatcher
import time
import json
import requests
import logging

_logger = logging.getLogger(__name__)

try:
    from mapbox import Geocoder
except ImportError:
    _logger.debug(u"Impossible d'importer la librairie Python 'mapbox.Geocoder'.")

CORRESPONDANCE_PRECISION_BANO = {
    'housenumber': 'very_high',
    'street': 'high',
    'locality': 'medium',
    'municipality': 'low',
    'other': 'unknown',
}
CORRESPONDANCE_PRECISION_MAPBOX = {
    'poi': 'very_high',
    'address': 'very_high',
    'neighborhood': 'high',
    'locality': 'medium',
    'place': 'low',
    'district': 'low',
    'postcode': 'low',
    'region': 'no_address',
    'other': 'unknown',
}


class OFGeoWizardMono(models.TransientModel):
    _name = "of.geo.wizard.mono"
    _description = u"Géocoder une adresse"

    @api.model
    def _get_geocodeurs(self):
        result = []
        partner_id = self._context.get('default_partner_id')
        if partner_id:
            partner = self.env['res.partner'].browse(partner_id)
            if not partner:
                return
            if partner.get_geocoding_country().upper() == 'FRANCE':
                result.append(('bano', u"Base d'Adresses Nationale (BANO)"))
            result.append(('mapbox', u"MapBox"))
        return result

    @api.onchange('partner_id')
    def onchange_partner_id(self):
        if self.partner_id:
            self.addr_search = self.partner_id.get_addr_params()

    @api.depends('line_id.score')
    @api.multi
    def _compute_score(self):
        for wizard in self:
            if wizard.line_id:
                wizard.line_score = "%s%%" % str(int(wizard.line_id.score * 100))
            else:
                wizard.line_score = "-"
            print wizard.line_score

    @api.multi
    @api.depends('line_id')
    def _compute_line_map_ids(self):
        for wizard in self:
            if wizard.line_id:
                wizard.line_map_ids = [(6, 0, [wizard.line_id.id])]
            else:
                wizard.line_map_ids = False

    partner_id = fields.Many2one('res.partner', string=u"Partenaire à géolocaliser", readonly=True)
    addr_search = fields.Char(string=u"Adresse à géocoder")
    geocodeur = fields.Selection(_get_geocodeurs, string=u"Géocodeur", default=lambda x: x._get_geocodeurs()[0])

    aucun_res = fields.Boolean(string="Aucun résultat")
    write_addr = fields.Boolean(string=u"Mettre à jour l'adresse du partenaire")

    line_ids = fields.One2many('of.geo.wizard.mono.line', 'wizard_id', string=u"Résultats")
    # One2many pour afficher sur une carte
    line_map_ids = fields.One2many('of.geo.wizard.mono.line', 'wizard_id', string=u"Résultats", compute="_compute_line_map_ids")
    line_id = fields.Many2one('of.geo.wizard.mono.line', string=u"Résultat", domain="[('wizard_id', '=', id)]")

    line_score = fields.Char(string="Score", compute="_compute_score")
    line_precision = fields.Selection(related="line_id.precision", readonly=True)
    line_geo_lat = fields.Float(related="line_id.geo_lat", readonly=True)
    line_geo_lng = fields.Float(related="line_id.geo_lng", readonly=True)
    line_street = fields.Char(related="line_id.street", readonly=True)
    line_zip = fields.Char(related="line_id.zip", readonly=True)
    line_city = fields.Char(related="line_id.city", readonly=True)
    line_country = fields.Char(related="line_id.country", readonly=True)

    @api.multi
    def button_search(self):
        self.ensure_one()
        if not self.addr_search:
            raise UserError(u"Vous devez entrer une adresse à géocoder pour pouvoir lancer une recherche")
        if not self.geocodeur:
            raise UserError(u"Vous devez choisir un géocodeur pour pouvoir lancer une recherche")
        if self.geocodeur == 'bano':
            self.geo_bano()
        if self.geocodeur == 'mapbox':
            self.geo_mapbox()
        return {"type": "ir.actions.do_nothing"}

    # Geocoding with BANO
    @api.multi
    def geo_bano(self):
        self.ensure_one()
        API_URL = "https://api-adresse.data.gouv.fr/search/?"
        addr_str = self.addr_search
        if addr_str.endswith(u", France"):
            addr_str = addr_str[:-8]
        params = {'q': addr_str, 'limit': '5', 'autocomplete': '1'}

        # Server query and response
        try:
            req = requests.get(API_URL, params=params)
            result = req.json()
        except Exception as e:
            raise UserError((u"Impossible de contacter le serveur de géolocalisation. Assurez-vous que votre connexion Internet est opérationnelle (%s)") % e)

        if not result or not result.get('features'):
            self.aucun_res = True
        else:
            line_ids_vals = [(5,)]
            for res in result.get('features'):
                coords = res.get("geometry", {}).get("coordinates")
                properties = res.get("properties", {})
                if not coords or not properties:
                    continue
                vals = {
                    'geo_lat': coords[1],
                    'geo_lng': coords[0],
                    'geocodeur': 'bano',
                    'geocoding': 'success_bano',
                    'name': properties.get("label", "") + u" France",
                    'street': properties.get("name", ""),
                    'zip': properties.get("postcode", ""),
                    'city': properties.get("city", ""),
                    'country': u"France",
                    'score': properties.get("score", 0),
                    'precision': CORRESPONDANCE_PRECISION_BANO.get(properties.get("type", "other"), u"unknown"),
                    'geocoding_response': json.dumps(res, indent=3, sort_keys=True, ensure_ascii=False),
                }
                line_ids_vals.append((0, 0, vals))
            if len(line_ids_vals) == 1:
                self.aucun_res = True
            self.line_ids = line_ids_vals
            self.line_id = self.line_ids and self.line_ids[0] or False
        return True

    # Géocodage avec OSM
    def geo_mapbox(self):
        # récupérer le token
        server_token = tools.config.get("of_token_mapbox", "")
        if not server_token:
            raise UserError(u"MapBox n'est pas correctement configuré.")

        # initialiser le geocodeur
        geocoder = Geocoder(access_token=server_token)

        try:
            result = geocoder.forward(self.addr_search).json()
        except Exception:
            raise UserError(u"Une erreur inattendue est survenue lors de la requête")

        if not result or not result.get('features'):
            self.aucun_res = True
        else:
            line_ids_vals = [(5, )]
            for res in result.get('features', []):
                coords = res.get("center", {})
                for elem in res.get('context', []):
                    if elem.get("id", u"").startswith(u"postcode"):
                        res['zip'] = elem.get("text")
                    if elem.get("id", u"").startswith(u"place"):
                        res['city'] = elem.get("text")
                    if elem.get("id", u"").startswith(u"country"):
                        res['country'] = elem.get("text")
                if not coords:
                    continue
                vals = {
                    'geo_lat': coords[1],
                    'geo_lng': coords[0],
                    'geocodeur': 'mapbox',
                    'geocoding': 'success_mapbox',
                    'name': res.get("place_name", ""),
                    'street': '%s %s' % (res.get("address", u""), res.get("text", u"")),
                    'zip': res.get("zip", ""),
                    'city': res.get("city", ""),
                    'country': res.get("country", ""),
                    'score': res.get("relevance", 0),
                    'precision': CORRESPONDANCE_PRECISION_MAPBOX.get(res.get("place_type", ["other"])[-1], u"unknown"),
                    'geocoding_response': json.dumps(res, indent=3, sort_keys=True, ensure_ascii=False),
                }
                line_ids_vals.append((0, 0, vals))
            if len(line_ids_vals) == 1:
                self.aucun_res = True
            self.line_ids = line_ids_vals
            self.line_id = self.line_ids and self.line_ids[0] or False

        return True

    @api.multi
    def button_confirm(self):
        self.ensure_one()
        if not self.line_id:
            raise UserError(u"Vous devez sélectionner un résultat avant de pouvoir valider")
        vals = {
            'geo_lat': self.line_id.geo_lat,
            'geo_lng': self.line_id.geo_lng,
            'geocodeur': self.line_id.geocodeur,
            'geocoding': self.line_id.geocoding,
            'precision': self.line_id.precision,
            'date_last_localization': fields.Date.today(),
            'geocoding_response': self.line_id.geocoding_response,
            'street_query': self.addr_search,
            'street_response': self.line_id.name,
        }
        if self.write_addr:
            vals['street'] = self.line_id.street
            vals['street2'] = False
            vals['zip'] = self.line_id.zip
            vals['city'] = self.line_id.city
        self.partner_id.write(vals)
        return True


class OFGeoWizardMonoLine(models.TransientModel):
    _name = "of.geo.wizard.mono.line"
    _description = u"Proposition de résultat d'adresse"
    _order = "wizard_id, geocodeur, score DESC"

    wizard_id = fields.Many2one('of.geo.wizard.mono', string="Wizard")

    name = fields.Char(string=u"Adresse proposée")
    partner_name = fields.Char(string="Nom du partenaire", related="wizard_id.partner_id.name", readonly=True)

    geocodeur = fields.Char(string=u"Géocodeur")
    geocoding = fields.Selection(
        [
            ('not_tried', u"Pas tenté"),
            ('no_address', u"--"),
            ('success_bano', u"Réussi"),
            ('success_google', u"Réussi"),
            ('success_mapbox', u"Réussi"),
            ('need_verif', u"Nécessite vérification"),
            ('failure', u"Échoué"),
            ('manual', u"Manuel")
        ], string=u"Géocoding")
    precision = fields.Selection(
        [
            ('manual', "Manuel"),
            ('very_high', "Excellent"),
            ('high', "Haut"),
            ('medium', "Moyen"),
            ('low', "Bas"),
            ('no_address', u"--"),
            ('unknown', u"Indéterminé"),
        ], default='unknown',
        help=u"Niveau de précision de la géolocalisation.\n"
             u"bas: à la ville.\n"
             u"moyen: au village\n"
             u"haut: à la rue / au voisinage\n"
             u"très haut: au numéro de rue\n")
    geocoding_response = fields.Text(string=u"Réponse géocodage", readonly=True)
    score = fields.Float(string="Score", digits=(1, 2), help=u"Nombre entre 0 et 1, \n0: aucun rapport, \n1: très bon")

    geo_lat = fields.Float(string="Latitude", digits=(4, 8))
    geo_lng = fields.Float(string="Latitude", digits=(4, 8))

    street = fields.Char(string=u"Rue")
    zip = fields.Char(string=u"Code postal")
    city = fields.Char(string=u"Ville")
    country = fields.Char(string=u"Pays")


class OFGeoWizard(models.TransientModel):
    _name = "of.geo.wizard"
    _description = u"Géocodage des partenaires sélectionnés"

    @api.model
    def _get_partner_ids(self):
        model = self._context.get('active_model')
        if not model:  # en cas de rafraichissement page: choisir les partenaires du dernier wizard
            wizard = self.env['of.geo.wizard'].browse()
            partners = wizard and wizard[-1].partner_ids or self.env['res.partner']
        else:
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

    @api.multi
    def _compute_name(self):
        for wizard in self:
            if wizard.line_ids:
                wizard.name = u"Vérifier et valider"
            else:
                wizard.name = u"Préparation du géocoding"

    name = fields.Char(string="Nom", compute="_compute_name")

    # Stats
    nb_partners = fields.Integer(string=u'Nb partenaires', compute='_compute_global_geo_stats', readonly=True)
    nb_geocoding_success_mapbox = fields.Integer(string=u'Geolocalisés avec MapBox', compute='_compute_global_geo_stats', readonly=True)
    nb_geocoding_success_ban = fields.Integer(string=u'Geolocalisés avec BANO', compute='_compute_global_geo_stats', readonly=True)
    nb_geocoding_manually = fields.Integer(string=u'Geolocalisés manuellement', compute='_compute_global_geo_stats', readonly=True)
    nb_geocoding_total_success = fields.Integer(string=u'Total geolocalisés', compute='_compute_global_geo_stats', readonly=True)
    nb_geocoding_failure = fields.Integer(string=u'Échec du géocodage', compute='_compute_global_geo_stats', readonly=True)
    nb_no_address = fields.Integer(string=u"Sans adresse", compute='_compute_global_geo_stats', readonly=True)
    nb_geocoding_not = fields.Integer(string=u'Non géolocalisés', compute='_compute_global_geo_stats', readonly=True)

    por_success_mapbox = fields.Float(digits=(3, 1), compute='_compute_global_geo_stats', readonly=True)
    por_success_ban = fields.Float(digits=(3, 1), compute='_compute_global_geo_stats', readonly=True)
    por_manually = fields.Float(digits=(3, 1), compute='_compute_global_geo_stats', readonly=True)
    por_total_success = fields.Float(digits=(3, 1), compute='_compute_global_geo_stats', readonly=True)
    por_failure = fields.Float(digits=(3, 1), compute='_compute_global_geo_stats', readonly=True)
    por_no_address = fields.Float(digits=(3, 1), compute='_compute_global_geo_stats', readonly=True)
    por_not = fields.Float(digits=(3, 1), compute='_compute_global_geo_stats', readonly=True)

    show_stats_wizard = fields.Boolean(string=u"Montrer statistiques", default=_get_config_stats)

    # Stats géocodeurs
    mapbox_try = 0
    mapbox_success = 0
    mapbox_fail = 0

    ban_try = 0
    ban_success = 0
    ban_fail = 0

    # Get taux success from last record in the of.geo.wizard
    @api.model
    def _get_taux_success_mapbox(self):
        try:
            last_record = self.env['of.geo.wizard'].search([])[-1]
            taux_success_mapbox = last_record.taux_success_mapbox
        except:
            taux_success_mapbox = ""
        return taux_success_mapbox

    @api.model
    def _get_taux_success_ban(self):
        try:
            last_record = self.env['of.geo.wizard'].search([])[-1]
            taux_success_ban = last_record.taux_success_ban
        except:
            taux_success_ban = ""
        return taux_success_ban

    taux_success_mapbox = fields.Float(default=_get_taux_success_mapbox, digits=(3, 1), readonly=True)
    taux_success_ban = fields.Float(default=_get_taux_success_ban, digits=(3, 1), readonly=True)

    # Options
    best_precision = fields.Boolean(string=u"Choisir la meilleure précision des géocodeurs sélectionnés (lente)", default=False)

    # Traitement de données déjà géolocalisées
    overwrite_if_failure = fields.Boolean(string=u"Écraser aussi en cas d'echec de géolocalisation", default=False)
    overwrite_geoloc_all = fields.Boolean(string=u"Écraser tous ceux sélectionnés", default=False)
    overwrite_geoloc_except_manual = fields.Boolean(string=u"Écraser tous ceux sélectionnés sauf ceux geolocalisés manuellement", default=False)

    # Selected Partners
    partner_ids = fields.Many2many('res.partner', string=u"Partenaires sélectionnés", default=_get_partner_ids)
    partner_id = fields.Many2one('res.partner', string=u"Partenaire à géocoder")
    country_name = fields.Char(string=u"Pays du partenaire", compute='_compute_partner_country_name')
    line_ids = fields.One2many('of.geo.wizard.line', 'wizard_id', string=u"partenaires à géocoder")
    selection_done = fields.Boolean(string=u"Sélection faite")

    nb_selected_partners = fields.Integer(string=u'Nb partenaires sélectionnés', compute='_compute_selected_stats', readonly=True)
    nb_selected_partners_success = fields.Integer(string=u'Nb partenaires sélectionnés reussi', compute='_compute_selected_stats', readonly=True)
    nb_selected_partners_failure = fields.Integer(string=u'Nb partenaires sélectionnés echoue', compute='_compute_selected_stats', readonly=True)
    nb_selected_partners_no_address = fields.Integer(string=u"Nb partenaires sélectionnés pas d'adresse", compute='_compute_selected_stats', readonly=True)
    nb_selected_partners_need_verif = fields.Integer(string=u"Nb partenaires sélectionnés Nécessitent vérification",
                                                     compute='_compute_selected_stats')
    nb_selected_partners_not = fields.Integer(string=u'Nb partenaires sélectionnés pas tentés', compute='_compute_selected_stats', readonly=True)
    nb_selected_partners_manual = fields.Integer(string=u'Nb partenaires sélectionnés manuel', compute='_compute_selected_stats', readonly=True)
    nb_selected_partners_to_geoloc = fields.Integer(string=u'Nb partenaires sélectionnés à géolocaliser', compute='_compute_selected_stats', readonly=True)

    @api.onchange('overwrite_geoloc_all', 'overwrite_geoloc_except_manual')
    def onchange_overwrite_geoloc(self):
        if not (self.overwrite_geoloc_all or self.overwrite_geoloc_except_manual):
            self.overwrite_if_failure = False

    @api.onchange('partner_id')
    def _compute_partner_country_name(self):
        self.country_name = self.partner_id.get_geocoding_country()

    @api.onchange('partner_ids', 'overwrite_geoloc_all', 'overwrite_geoloc_except_manual')
    def _compute_selected_stats(self):
        partners = self.line_ids or self.partner_ids
        self.nb_selected_partners = len(partners)
        self.nb_selected_partners_success = len(partners.filtered(lambda p: p.geocoding in (
            'success_openfire', 'success_osm', 'success_mapbox', 'success_bano', 'success_google', 'manual')))
        self.nb_selected_partners_failure = len(partners.filtered(lambda p: p.geocoding == 'failure'))
        self.nb_selected_partners_no_address = len(partners.filtered(lambda p: p.geocoding == 'no_address'))
        self.nb_selected_partners_need_verif = len(partners.filtered(lambda p: p.geocoding == 'need_verif'))
        self.nb_selected_partners_manual = len(partners.filtered(lambda p: p.geocoding == 'manual'))
        self.nb_selected_partners_not = len(partners.filtered(lambda p: p.geocoding == 'not_tried'))

        if self.overwrite_geoloc_all:
            self.nb_selected_partners_to_geoloc = self.nb_selected_partners - self.nb_selected_partners_no_address
        elif self.overwrite_geoloc_except_manual:
            self.nb_selected_partners_to_geoloc = self.nb_selected_partners - self.nb_selected_partners_no_address - self.nb_selected_partners_manual
        else:
            self.nb_selected_partners_to_geoloc = self.nb_selected_partners - self.nb_selected_partners_no_address - self.nb_selected_partners_success

    @api.depends('partner_ids')
    def _compute_global_geo_stats(self):
        partner_obj = self.env["res.partner"]
        partners = partner_obj.search([])

        # Get
        nb_partners = len(partners)
        nb_geocoding_success_mapbox = partner_obj.search([('geocoding', '=', 'success_mapbox')], count=True)
        nb_geocoding_success_ban = partner_obj.search([('geocoding', '=', 'success_bano')], count=True)
        nb_geocoding_total_success = partner_obj.search([('geocoding', '=like', 'success\\_%')], count=True)
        nb_geocoding_manually = partner_obj.search([('geocoding', '=', 'manual')], count=True)
        nb_geocoding_failure = partner_obj.search([('geocoding', '=', 'failure')], count=True)
        nb_no_address = partner_obj.search([('geocoding', '=', 'no_address')], count=True)
        nb_geocoding_not = partner_obj.search([('geocoding', '=', 'not_tried')], count=True)

        # Calcule
        por_success_mapbox = float(nb_geocoding_success_mapbox) / float(nb_partners) * 100
        por_success_ban = float(nb_geocoding_success_ban) / float(nb_partners) * 100
        por_manually = float(nb_geocoding_manually) / float(nb_partners) * 100
        por_total_success = float(nb_geocoding_total_success) / float(nb_partners) * 100
        por_failure = float(nb_geocoding_failure) / float(nb_partners) * 100
        por_no_address = float(nb_no_address) / float(nb_partners) * 100
        por_not = float(nb_geocoding_not) / float(nb_partners) * 100

        # Return
        self.nb_partners = nb_partners
        self.nb_geocoding_success_mapbox = nb_geocoding_success_mapbox
        self.nb_geocoding_success_ban = nb_geocoding_success_ban
        self.nb_geocoding_manually = nb_geocoding_manually
        self.nb_geocoding_total_success = nb_geocoding_total_success
        self.nb_geocoding_failure = nb_geocoding_failure
        self.nb_no_address = nb_no_address
        self.nb_geocoding_not = nb_geocoding_not

        self.por_success_mapbox = por_success_mapbox
        self.por_success_ban = por_success_ban
        self.por_manually = por_manually
        self.por_total_success = por_total_success
        self.por_failure = por_failure
        self.por_no_address = por_no_address
        self.por_not = por_not

    # Funcion to check string similarity [difflib]
    def similar(self, a, b):
        return SequenceMatcher(None, a, b).ratio()

    # Géocodage avec Mapbox
    def geo_mapbox(self, partner):
        # récupérer le token
        server_token = tools.config.get("of_token_mapbox", "")
        if not server_token:
            raise UserError(u"MapBox n'est pas correctement configuré.")

        if partner._name == 'res.partner':
            addr_str = partner.get_addr_params()
        elif partner._name == 'of.geo.wizard.line':
            addr_str = partner.street_query
        else:
            addr_str = False

        if not addr_str:
            geocoding = 'no_address'
            geocodeur = ""
            latitud = 0
            longitud = 0
            precision = 'no_address'
            geocoding_response = ""
            street_response = ""
        else:
            # initialiser le geocodeur
            geocoder = Geocoder(access_token=server_token)
            geocodeur = 'mapbox'
            try:
                res = geocoder.forward(addr_str).json()
                self.mapbox_try += 1
            except Exception as e:
                return 'not_tried', "", 0, 0, 'not_tried', e, ""
            if not res or not res.get('features'):
                self.mapbox_fail += 1
                geocoding = 'failure'
                latitud = 0
                longitud = 0
                precision = "unknown"
                geocoding_response = ""
                street_response = ""
            else:
                res = res.get('features')[0]
                coords = res.get("center", [0, 0])
                latitud = coords[1]
                longitud = coords[0]
                score = res.get("relevance", 0)
                precision = CORRESPONDANCE_PRECISION_MAPBOX.get(res.get("place_type", ["other"])[-1], u"unknown")
                geocoding_response = json.dumps(res, indent=3, sort_keys=True, ensure_ascii=False)
                street_response = res.get("place_name", "")
                if score < 0.5 or latitud == 0 or longitud == 0:
                    self.mapbox_fail += 1
                    geocoding = 'failure'
                elif score < 0.7:
                    geocoding = 'need_verif'
                else:
                    geocoding = 'success_mapbox'
                    self.mapbox_success += 1

        return geocoding, geocodeur, latitud, longitud, precision, geocoding_response, street_response

    # Geocoding with BANO
    def geo_ban(self, partner):
        # Variables
        geocodeur = 'bano'

        # Start
        API_URL = "https://api-adresse.data.gouv.fr/search/?"

        # Get address data
        if partner._name == 'res.partner':
            query = partner.get_addr_params()
        elif partner._name == 'of.geo.wizard.line':
            query = partner.street_query
        else:
            query = False
        if not query:
            geocoding = 'no_address'
            geocodeur = ""
            latitud = 0
            longitud = 0
            precision = 'no_address'
            geocoding_response = ""
            street_response = ""
        else:
            params = {
                'q': query,
                'limit': '1',
            }

            # Server query and response
            try:
                req = requests.get(API_URL, params=params)
                res = req.json()
                self.ban_try += 1
            except Exception:
                return 'not_tried', "", 0, 0, 'not_tried', "", ""

            if not res or not res.get('features'):
                self.ban_fail += 1
                geocoding = 'failure'
                latitud = 0
                longitud = 0
                precision = "unknown"
                geocoding_response = ""
                street_response = ""
            else:
                res = res.get('features')[0]
                coords = res.get("geometry", {}).get("coordinates")
                properties = res.get("properties", {})
                if not coords or properties.get('score', 0) < 0.65:
                    self.ban_fail += 1
                    geocoding = 'failure'
                    latitud = 0
                    longitud = 0
                    precision = "unknown"
                    geocoding_response = ""
                    street_response = ""
                else:
                    self.ban_success += 1
                    geocoding = 'success_bano'
                    latitud = coords[1]
                    longitud = coords[0]
                    precision = CORRESPONDANCE_PRECISION_BANO.get(properties.get("type", "other"), u"unknown")
                    geocoding_response = json.dumps(res, indent=3, sort_keys=True, ensure_ascii=False)
                    street_response = properties.get("label", "") + u" France"

        return geocoding, geocodeur, latitud, longitud, precision, geocoding_response, street_response

    # Erase button
    @api.multi
    def action_reset_geo_val_selected(self):
        for partner in self.partner_ids:
            if not partner.geocoding == 'manual':  # Protect manual geocoding
                partner.write({
                    'geocoding': 'not_tried',
                    'geocodeur': 'unknown',
                    'geo_lat': 0,
                    'geo_lng': 0,
                    'precision': 'not_tried',
                    'date_last_localization': fields.Datetime.context_timestamp(self, fields.datetime.now()),
                    'geocoding_response': u"Réinitialisé",
                })
        return {"type": "ir.actions.do_nothing"}

    def action_button_geo_mapbox(self):
        partner_id = self._context.get('active_id')
        if not partner_id:
            raise UserError(u"Un partenaire doit être fourni")
        partner = self.env['res.partner'].browse(partner_id)

        results = self.geo_mapbox(partner)

        to_update = True
        if (partner.geo_lat != 0 or partner.geo_lng != 0) and not self.overwrite_if_failure and \
                results[0] == 'failure':
            to_update = False
        if to_update:
            partner.write({
                'geocoding': results[0],
                'geocodeur': results[1],
                'geo_lat': results[2],
                'geo_lng': results[3],
                'precision': results[4],
                'date_last_localization': fields.Datetime.context_timestamp(self, fields.datetime.now()),
                'geocoding_response': results[5],
                'street_response': results[6],
            })
        return True

    def action_button_geo_ban(self):
        partner_id = self._context.get('active_id')
        if not partner_id:
            raise UserError(u"Un partenaire doit être fourni")
        partner = self.env['res.partner'].browse(partner_id)

        results = self.geo_ban(partner)
        to_update = True
        if (partner.geo_lat != 0 or partner.geo_lng != 0) and not self.overwrite_if_failure and \
                results[0] == 'failure':
            to_update = False
        if to_update:
            partner.write({
                'geocoding': results[0],
                'geocodeur': results[1],
                'geo_lat': results[2],
                'geo_lng': results[3],
                'precision': results[4],
                'date_last_localization': fields.Datetime.context_timestamp(self, fields.datetime.now()),
                'geocoding_response': results[5],
                'street_response': results[6],
            })
        return True

    def action_button_reset_geo_val(self):
        # Geocoding manual = False (Delete manual records too)
        if self.partner_ids.geocoding == 'manual':
            self.partner_ids.geocoding = "not_tried"

        self.action_reset_geo_val_selected()
        return True

    @api.multi
    def button_verify_geocoding(self, line_id):
        self.ensure_one()
        line = self.env['of.geo.wizard.line'].browse(line_id)
        if line.geocodeur == 'bano':
            if line.geocoding != 'success_bano':
                self.ban_success += 1
            line.geocoding = 'success_bano'
        elif line.geocodeur == 'mapbox':
            if line.geocoding != 'success_mapbox':
                self.mapbox_success += 1
            line.geocoding = 'success_mapbox'
        return True

    @api.multi
    def button_refute_geocoding(self, line_id):
        self.ensure_one()
        line = self.env['of.geo.wizard.line'].browse(line_id)
        if line.geocoding == 'success_mapbox':
            self.mapbox_success -= 1
        elif line.geocoding == 'success_bano':
            self.ban_success -= 1
        elif line.geocoding != 'failure' and line.geocodeur == 'bano':
            self.ban_fail += 1
        elif line.geocoding != 'failure' and line.geocodeur == 'mapbox':
            self.mapbox_fail += 1
        line.geocoding = 'failure'
        return True

    @api.multi
    def button_try_again(self, line_id):
        self.ensure_one()
        line = self.env['of.geo.wizard.line'].browse(line_id)
        partner_country = line.partner_id.get_geocoding_country()
        # On essaie d'abord bano puis mapbox
        if partner_country == u"France":
            geocoding, geocodeur, latitud, longitud, precision, geocoding_response, street_response = self.geo_ban(line)
            if geocoding == 'success_bano':
                line.write({
                    'geocoding': geocoding,
                    'geocodeur': 'bano',
                    'geo_lat': latitud,
                    'geo_lng': longitud,
                    'precision': precision,
                    'geocoding_response': geocoding_response,
                    'street_response': street_response,
                })
                return True
        geocoding, geocodeur, latitud, longitud, precision, geocoding_response, street_response = self.geo_mapbox(line)
        line.write({
            'geocoding': geocoding,
            'geocodeur': 'mapbox',
            'geo_lat': latitud,
            'geo_lng': longitud,
            'precision': precision,
            'geocoding_response': geocoding_response,
            'street_response': street_response,
        })
        return True

    @api.multi
    def button_confirm(self):
        self.ensure_one()
        date_last_localization = fields.Datetime.context_timestamp(self, fields.datetime.now())
        for line in self.line_ids:
            vals = {
                'geo_lat': line.geo_lat,
                'geo_lng': line.geo_lng,
                'geocodeur': line.geocodeur,
                'geocoding': line.geocoding,
                'precision': line.precision,
                'street_query': line.street_query,
                'street_response': line.street_response,
                'geocoding_response': line.geocoding_response,
                'date_last_localization': date_last_localization,
            }
            if line.geocoding not in ('success_mapbox', 'success_bano', 'need_verif'):
                vals['geo_lat'] = 0
                vals['geo_lng'] = 0
                vals['precision'] = 'unknown'
            line.partner_id.write(vals)
        return {'type': 'ir.actions.client', 'tag': 'history_back'}

    # GEOCODING BY LOT (Geolocalizer button)
    @api.multi
    def action_geocode(self):
        # count writes, commit each 100 writes
        cmpt = 0
        # limiter les requetes par seconde
        cmpt_req = 0
        self.selection_done = True

        # première vague de géocoding avec BANO
        # au moins un français?
        pays = self.partner_ids.mapped('country_id').mapped('name')
        for p in pays:
            if p == u"France":
                use_bano = True
                break
        else:
            use_bano = False

        line_vals = [(5, )]
        for partner in self.partner_ids:
            if (
                self.overwrite_geoloc_all or
                (self.overwrite_geoloc_except_manual and partner.geocoding != 'manual') or
                partner.geocoding in ('not_tried', 'need_verif', 'failure')
            ):
                vals = {
                    'partner_id': partner.id,
                    'street_query': partner.get_addr_params(),
                    'geocoding': 'not_tried',
                    'geocodeur': u"Indéterminé",
                    'precision': 'not_tried',
                    'geo_lat': 0,
                    'geo_lng': 0,
                }
                line_vals.append((0, 0, vals))
        self.line_ids = line_vals

        # SECUENTIAL GEOCODING
        for use_geocoder, geocoder_function, geocoder_name in (
            (use_bano, self.geo_ban, 'ban'),
            (True, self.geo_mapbox, 'mapbox'),
        ):
            for line in self.line_ids:
                if line.geocoding == 'success_bano':
                    continue
                partner = line.partner_id
                partner_country = partner.get_geocoding_country()
                if geocoder_name == 'ban' and partner_country != u'France':
                    continue
                # limitation du nomre de requètes par secondes: bano = 50, mapbox = 10
                if geocoder_name == 'ban' and cmpt_req % 50 == 0 or cmpt_req % 10 == 0:
                    time.sleep(1)
                results = geocoder_function(partner)
                cmpt_req += 1
                to_update = True
                if (line.geo_lat != 0 or line.geo_lng != 0) and not self.overwrite_if_failure and results[0] == 'failure':
                    to_update = False
                if to_update:
                    line.write({
                        'geocoding': results[0],
                        'geocodeur': results[1],
                        'geo_lat': results[2],
                        'geo_lng': results[3],
                        'precision': results[4],
                        'geocoding_response': results[5],
                        'street_response': results[6],
                    })
                    cmpt += 1

            # Stats geocoders
            try:
                taux_success = float(getattr(self, '%s_success' % geocoder_name)) / float(getattr(self, '%s_try' % geocoder_name)) * 100
                taux_success = float("{0:.2f}".format(taux_success))
                self['taux_success_%s' % geocoder_name] = taux_success
            except Exception:
                self['taux_success_%s' % geocoder_name] = ""

            if cmpt % 100 == 0:
                self._cr.commit()

        return {"type": "ir.actions.do_nothing"}


class OFGeoWizardLine(models.TransientModel):
    _name = "of.geo.wizard.line"
    _description = u"Géocodage des partenaires sélectionnés"
    _order = "sequence"

    wizard_id = fields.Many2one('of.geo.wizard', string="Wizard")

    partner_id = fields.Many2one('res.partner', string=u"Partenaire")
    name = fields.Char(string="Nom du partenaire", related="partner_id.name", readonly=True)

    geocodeur = fields.Char(string=u"Géocodeur", readonly=True)
    geocoding = fields.Selection(
        [
            ('not_tried', u"Pas tenté"),
            ('no_address', u"--"),
            ('success_bano', u"Réussi"),
            ('success_google', u"Réussi"),
            ('success_mapbox', u"Réussi"),
            ('need_verif', u"Nécessite vérification"),
            ('failure', u"Échoué"),
            ('manual', u"Manuel")
        ], string=u"Géocoding", readonly=True)
    precision = fields.Selection(
        [
            ('manual', "Manuel"),
            ('very_high', "Excellent"),
            ('high', "Haut"),
            ('medium', "Moyen"),
            ('low', "Bas"),
            ('no_address', u"--"),
            ('unknown', u"Indéterminé"),
            ('not_tried', u"Pas tenté"),
        ], default='not_tried', readonly=True,
        help=u"Niveau de précision de la géolocalisation.\n"
             u"bas: à la ville.\n"
             u"moyen: au village\n"
             u"haut: à la rue / au voisinage\n"
             u"très haut: au numéro de rue\n")
    geocoding_response = fields.Text(string=u"Réponse géocodage", readonly=True)
    score = fields.Float(string="Score", digits=(1, 2), help=u"Nombre entre 0 et 1, \n0: aucun rapport, \n1: très bon")
    sequence = fields.Integer(store=True, compute="_compute_sequence")

    street_query = fields.Char(string=u"Adresse requète")
    street_response = fields.Char(string=u"Adresse trouvée", readonly=True)
    geo_lat = fields.Float(string="Latitude", digits=(4, 8))
    geo_lng = fields.Float(string="Latitude", digits=(4, 8))

    street = fields.Char(string=u"Rue")
    zip = fields.Char(string=u"Code postal")
    city = fields.Char(string=u"Ville")
    country = fields.Char(string=u"Pays")

    @api.multi
    @api.depends('geocoding', 'precision')
    def _compute_sequence(self):
        for line in self:
            sequence = 15
            if line.geocoding == 'need_verif':
                sequence -= 10
            elif line.geocoding == 'failure':
                sequence -= 5
            if line.precision == 'low':
                sequence -= 4
            elif line.precision == 'medium':
                sequence -= 3
            elif line.precision == 'high':
                sequence -= 2
            line.sequence = sequence

    @api.multi
    def button_verify_geocoding(self):
        return self.wizard_id.button_verify_geocoding(self.id)

    @api.multi
    def button_refute_geocoding(self):
        return self.wizard_id.button_refute_geocoding(self.id)

    @api.multi
    def button_try_again(self):
        return self.wizard_id.button_try_again(self.id)
