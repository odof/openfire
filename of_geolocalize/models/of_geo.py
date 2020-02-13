# -*- coding: utf-8 -*-

# Requires a nominatim server up and running (for OpenFire geocoder in wizard)
# Requires request and googlemaps python packages (for Google Maps geocoder in wizard)

from odoo import api, fields, models

import json

# Add geocoding fields to res.company model (all are related to partner_id)
class ResCompany(models.Model):
    _inherit = "res.company"

    geo_lat = fields.Float(string='Geo Lat', digits=(8, 8), related='partner_id.geo_lat', help="latitude field")
    geo_lng = fields.Float(string='Geo Lng', digits=(8, 8), related='partner_id.geo_lng', help="longitude field")
    date_last_localization = fields.Datetime(string='Last Geolocation Date', related='partner_id.date_last_localization', readonly=True)
    geocoding_response = fields.Text(string=u"Réponse géocadage", related='partner_id.geocoding_response', readonly=True)
    geocoding = fields.Selection([
        ('not_tried', u"Pas tenté"),
        ('no_address', u"--"),
        ('success_openfire', u"Réussi"),
        ('success_osm', u"Réussi"),
        ('success_bano', u"Réussi"),
        ('success_google', u"Réussi"),
        ('failure', u"Échoué"),
        ('manual', u"Manuel")
        ], default='not_tried', readonly=True, help="field defining the state of the geocoding for this partner", related='partner_id.geocoding')
    geocodeur = fields.Selection([
        ('nominatim_openfire', u"OpenFire"),
        ('nominatim_osm', u"OpenStreetMap"),
        ('bano', u"BANO"),
        ('google_maps', u"Google Maps"),
        ('manual', u"Manuel"),
        ('unknown', u"Indéterminé")
        ], default='unknown', readonly=True, related='partner_id.geocodeur', help=u"Champ définissant le géocodeur utilisé")
    precision = fields.Selection([
        ('manual', "Manuel"),
        ('high', "Haut"),
        ('medium', "Moyen"),
        ('low', "Bas"),
        ('no_address', u"--"),
        ('unknown', u"Indéterminé"),
        ('not_tried', u"Pas tenté"),
        ], default='not_tried', readonly=True, related='partner_id.precision', help=u"Niveau de précision de la géolocalisation")
    street_query = fields.Char(string=u"Adresse requête", related='partner_id.street_query', readonly=True)


# Add geocoding parameters to res.partner model
class ResPartner(models.Model):
    _inherit = "res.partner"

    geo_lat = fields.Float(string='Geo Lat', digits=(8, 8), group_operator=False, help="latitude field")
    geo_lng = fields.Float(string='Geo Lng', digits=(8, 8), group_operator=False, help="longitude field")
    date_last_localization = fields.Datetime(string='Last Geolocation Date', readonly=True)
    geocoding_response = fields.Text(string=u"Réponse géocodage", readonly=True)
    geocoding = fields.Selection([
        ('not_tried', u"Pas tenté"),
        ('no_address', u"--"),
        ('success_openfire', u"Réussi"),
        ('success_osm', u"Réussi"),
        ('success_bano', u"Réussi"),
        ('success_google', u"Réussi"),
        ('failure', u"Échoué"),
        ('manual', u"Manuel")
        ], default='not_tried', readonly=True, help="field defining the state of the geocoding for this partner", required=True)
    geocodeur = fields.Selection([
        ('nominatim_openfire', u"OpenFire"),
        ('nominatim_osm', u"OpenStreetMap"),
        ('bano', u"BANO"),
        ('google_maps', u"Google Maps"),
        ('manual', u"Manuel"),
        ('unknown', u"Indéterminé")
        ], default='unknown', readonly=True, help=u"Champ définissant le géocodeur utilisé")
    precision = fields.Selection([
        ('manual', "Manuel"),
        ('high', "Haut"),
        ('medium', "Moyen"),
        ('low', "Bas"),
        ('no_address', u"--"),
        ('unknown', u"Indéterminé"),
        ('not_tried', u"Pas tenté"),
        ], default='not_tried', readonly=True, help=u"Niveau de précision de la géolocalisation")
    street_query = fields.Char(string=u"Adresse requête", readonly=True)

    def get_geocoding_country(self):
        return (self.country_id and self.country_id.name) or \
               (self.env.user.company_id.country_id and self.env.user.company_id.country_id.name) or u"France"

    # Get address data from db (same format for all geocoders)
    def get_addr_params(self):
        if not (self.zip or self.city):
            # Avoid requests with incomplete data
            return ""

        country = self.get_geocoding_country()

        # zip is not number (test france only)
        if self.zip:
            if country.upper() == "FRANCE":
                if not self.zip.strip().isdigit():
                    return ""

        params = [
            filter(lambda c: c != u',', self.street or '') + ' ' +
            filter(lambda c: c != u',', self.street2 or ''),
            self.zip or '' + ' ' + self.city or '',
            country,
        ]
        params = [p and p.strip() for p in params]
        params = [p for p in params if p]
        return ", ".join(params)

    @api.multi
    def geo_code(self, geocodeur=False):
        geo_obj = self.env['of.geo.wizard']
        if not geocodeur:
            geocodeur = self.env['ir.config_parameter'].get_param('geocoder_by_default')
        geocode = {
            'nominatim_openfire': geo_obj.geo_openfire,
            'nominatim_osm': geo_obj.geo_osm,
            'bano': geo_obj.geo_ban,
            'google_maps': geo_obj.geo_google,
        }.get(geocodeur, geo_obj.geo_openfire)
        for partner in self:
            results = geocode(partner)
            partner.write({
                'geocoding': results[0],
                'geocodeur': results[1],
                'geo_lat': results[2],
                'geo_lng': results[3],
                'precision': results[4],
                'date_last_localization': fields.Datetime.context_timestamp(self, fields.datetime.now()),
                'geocoding_response': json.dumps(results, indent=3, sort_keys=True, ensure_ascii=False),
            })

    # Conditional create when new partner is added
    @api.model
    def create(self, vals):
        """
        On partner creation geocode if an address is specified, setting geocoding_on_create
        is activate and it does not come from import (this only works in of_import)
        """
        partner = super(ResPartner, self).create(vals)

        if self.env['ir.config_parameter'].get_param('geocoding_on_create') == "yes" and not self._context.get('from_import'):
            # Check address parameters
            if (partner.street or partner.street2) and (partner.zip or partner.city):
                # Get geocoder by default
                res_geocoder_by_default = self.env['ir.config_parameter'].get_param('geocoder_by_default')

                # Reset geocoder use
                use_openfire = use_osm = use_bano = use_google = False

                # Set geocoder by default
                if not res_geocoder_by_default or res_geocoder_by_default == 'nominatim_openfire':
                    use_openfire = True
                elif res_geocoder_by_default == 'nominatim_osm':
                    use_osm = True
                elif res_geocoder_by_default == 'bano':
                    use_bano = True
                elif res_geocoder_by_default == 'google_maps':
                    use_google = True

                # Create wizard objet to do the action
                wizard_obj = self.env['of.geo.wizard']
                wizard = wizard_obj.with_context(active_ids=partner.id, active_model='res.partner').create({
                    'use_nominatim_openfire': use_openfire,
                    'use_nominatim_osm': use_osm,
                    'use_bano': use_bano,
                    'use_google': use_google,
                    'best_precision': False,
                    'overwrite_geoloc_all': True,
                    'overwrite_geoloc_except_manual': False,
                })
                wizard.action_geocode()
        return partner

    # Conditional writing when partner address or GPS coordinates are modified
    @api.multi
    def write(self, vals):
        # Get config paramenter geocoding on write
        res_geocoding_on_write = self.env['ir.config_parameter'].get_param('geocoding_on_write') == 'yes'

        # Determine if geocoding was manual and write geodata for it.
        do_geocoding_auto = False

        # Change coordinates but not geocoding (geo data manual entry)
        if ('geo_lat' in vals or 'geo_lng' in vals) and 'geocoding' not in vals:
            vals['geocoding'] = "manual"
            vals['geocodeur'] = "manual"
            vals['precision'] = "manual"
            vals['date_last_localization'] = fields.Datetime.context_timestamp(self, fields.datetime.now())
        elif (
            any(field in vals for field in ('street', 'street2', 'zip', 'city', 'state_id', 'country_id')) and
            not any(field in vals for field in ('geocoding', 'geocodeur', 'date_last_localization', 'precision'))
        ):
            if res_geocoding_on_write:  # Do geocoding automatic
                do_geocoding_auto = True
            else:  # if config gecoding on write False, set as not tried
                vals['geocoding'] = "not_tried"
                vals['geocodeur'] = "unknown"
                vals['geo_lat'] = 0
                vals['geo_lng'] = 0
                vals['precision'] = "not_tried"
                vals['date_last_localization'] = fields.Datetime.context_timestamp(self, fields.datetime.now())

        result = super(ResPartner, self).write(vals)

        # DO GEOCODING AUTOMATIC (through wizard)
        if do_geocoding_auto:
            # Get geocoder by default
            res_geocoder_by_default = self.env['ir.config_parameter'].get_param('geocoder_by_default')

            # Ne pas utiliser BANO si le pays n'est pas la France
            if res_geocoder_by_default == 'bano':
                for rec in self:
                    if rec.get_geocoding_country() != u"France":
                        res_geocoder_by_default = 'nominatim_osm'
                        break

            # Reset geocoder use
            use_openfire = use_osm = use_bano = use_google = False

            # Set geocoder by default
            if not res_geocoder_by_default or res_geocoder_by_default == 'nominatim_openfire':
                use_openfire = True
            elif res_geocoder_by_default == 'nominatim_osm':
                use_osm = True
            elif res_geocoder_by_default == 'bano':
                use_bano = True
            elif res_geocoder_by_default == 'google_maps':
                use_google = True

            # Create wizard objet to do the action
            wizard_obj = self.env['of.geo.wizard']
            wizard = wizard_obj.with_context(active_ids=self._ids, active_model='res.partner').create({
                'use_nominatim_openfire': use_openfire,
                'use_nominatim_osm': use_osm,
                'use_bano': use_bano,
                'use_google': use_google,
                'best_precision': False,
                'overwrite_geoloc_all': True,
                'overwrite_geoloc_except_manual': False,
                'overwrite_if_failure': True,
            })
            wizard.action_geocode()
        return result


# Configuration
class OFGeoConfiguration(models.TransientModel):
    _name = 'of.geo.config.settings'
    _inherit = 'res.config.settings'

    @api.model_cr_context
    def _auto_init(self):
        # A supprimer : conversion de système d'enregistrement du géocodeur par défaut
        self._cr.execute(
            "UPDATE ir_config_parameter "
            "SET value = "
            "CASE value "
            " WHEN '0' THEN 'nominatim_openfire'"
            " WHEN '1' THEN 'nominatim_osm'"
            " WHEN '2' THEN 'bano'"
            " WHEN '3' THEN 'google_maps'"
            " ELSE value "
            "END "
            "WHERE key = 'geocoder_by_default'")
        on_write = self.env['ir.config_parameter'].get_param('geocoding_on_write', None)
        on_create = self.env['ir.config_parameter'].get_param('geocoding_on_create', None)
        if on_write is not None and on_write in ('0', '1'):
            self.env['ir.config_parameter'].set_param('geocoding_on_write', 'yes' if on_write == '1' else 'no')
        if on_create is not None and on_create in ('0', '1'):
            self.env['ir.config_parameter'].set_param('geocoding_on_create', 'yes' if on_create == '1' else 'no')
        return super(OFGeoConfiguration, self)._auto_init()

    # Check, get and prefill URLs geocoders
    @api.multi
    def _get_openfire_url(self):
        return self.env['ir.config_parameter'].get_param('url_openfire', '').strip()

    @api.model
    def _get_openfire_url_status(self):
        url_openfire_saved = self.env['ir.config_parameter'].get_param('url_openfire', '').strip()
        suggest_url_openfire = 'https://openfire.fr/nominatim/search?q='
        if url_openfire_saved and url_openfire_saved == suggest_url_openfire:
            openfire_url_status = 'ok'
        elif url_openfire_saved and url_openfire_saved.startswith('https://'):
            openfire_url_status = 'new'
        else:
            openfire_url_status = 'fail'
        return openfire_url_status

    @api.multi
    def _get_osm_url(self):
        return self.env['ir.config_parameter'].get_param('url_osm', '').strip()

    @api.model
    def _get_osm_url_status(self):
        url_osm_saved = self.env['ir.config_parameter'].get_param('url_osm', '').strip()
        suggest_url_osm = 'https://nominatim.openstreetmap.org/search?q='
        if url_osm_saved and url_osm_saved == suggest_url_osm:
            osm_url_status = 'ok'
        elif url_osm_saved and url_osm_saved.startswith('https://'):
            osm_url_status = 'new'
        else:
            osm_url_status = 'fail'
        return osm_url_status

    @api.multi
    def _get_bano_url(self):
        return self.env['ir.config_parameter'].get_param('url_bano', '').strip()

    @api.model
    def _get_bano_url_status(self):
        url_bano_saved = self.env['ir.config_parameter'].get_param('url_bano', '').strip()
        suggest_url_bano = 'https://api-adresse.data.gouv.fr/search/?'
        if url_bano_saved and url_bano_saved == suggest_url_bano:
            bano_url_status = 'ok'
        elif url_bano_saved and url_bano_saved.startswith('https://'):
            bano_url_status = 'new'
        else:
            bano_url_status = 'fail'
        return bano_url_status

    @api.multi
    def _get_google_url(self):
        return self.env['ir.config_parameter'].get_param('url_google', '').strip()

    @api.model
    def _get_google_url_status(self):
        url_google_saved = self.env['ir.config_parameter'].get_param('url_google', '').strip()
        suggest_url_google = 'http://maps.googleapis.com/maps/api/geocode/json'
        if url_google_saved and url_google_saved == suggest_url_google:
            google_url_status = 'ok'
        elif url_google_saved and url_google_saved.startswith('https://'):
            google_url_status = 'new'
        else:
            google_url_status = 'fail'
        return google_url_status

    # Check, get and prefill Google API key
    @api.multi
    def _get_google_api_key(self):
        return self.env['ir.config_parameter'].get_param('google_api_key', '').strip()

    @api.model
    def _get_google_api_key_status(self):
        saved_google_api_key = self.env['ir.config_parameter'].get_param('google_api_key', '').strip()
        if saved_google_api_key and len(saved_google_api_key) == 39:
            google_api_key_status = 1
        else:
            google_api_key_status = 0
        return google_api_key_status

    @api.model
    def _get_default_show_stats(self):
        return self.env['ir.config_parameter'].get_param('show_stats', '')

    @api.model
    def _get_default_geocoding_on_write(self):
        return self.env['ir.config_parameter'].get_param('geocoding_on_write', '')

    @api.model
    def _get_default_geocoding_on_create(self):
        return self.env['ir.config_parameter'].get_param('geocoding_on_create', '')

    @api.model
    def _get_default_geocoder_by_default(self):
        return self.env['ir.config_parameter'].get_param('geocoder_by_default', '')

    # Config fields
    url_openfire = fields.Char(string=u"OpenFire", default=_get_openfire_url)
    url_osm = fields.Char(string=u"OpenStreetMap", default=_get_osm_url)
    url_bano = fields.Char(string=u"BANO", default=_get_bano_url)
    url_google = fields.Char(string=u"Google Maps", default=_get_google_url)
    google_api_key = fields.Char(string=u"Google API key", size=40, default=_get_google_api_key)

    url_openfire_status = fields.Char(string="Status URL OpenFire", default=_get_openfire_url_status)
    url_osm_status = fields.Char(string="Status URL OpenStreetMap", default=_get_osm_url_status)
    url_bano_status = fields.Char(string="Status URL BANO", default=_get_bano_url_status)
    url_google_status = fields.Char(string="Status URL Google", default=_get_google_url_status)
    google_api_key_status = fields.Boolean(string="Status Google API key", default=_get_google_api_key_status)

    show_stats = fields.Boolean(string=u'Afficher stats', default=_get_default_show_stats)
    geocoding_on_write = fields.Selection([
        ('no', u"Ne pas recalculer les valeurs du géocodage automatiquement (Les coordonnées GPS sont remises à zéro si elles ne sont pas entrées en même temps.)"),
        ('yes', u"Recalculer les valeurs de géocodage (Le géocodage est tenté si les coordonnées GPS ne sont pas entrées en même temps.)"),
        ], u"Si une adresse est modifiée", default=_get_default_geocoding_on_write,
        help=u"Recalculer automatiquement les valeurs de géocodage lorsque l'adresse d'un partenaire est modifiée")
    geocoding_on_create = fields.Selection([
        ('no', u"Ne pas calculer les valeurs de géocodage (recommandé lorsqu'un grand nombre de partenaires sont importés)"),
        ('yes', u"Calculer les valeurs de géocodage automatiquement"),
        ], u"Si un partenaire est ajouté", default=_get_default_geocoding_on_create,
        help=u"Calculer automatiquement les valeurs de géocodage lorsqu'un nouveau partenaire est ajouté")
    geocoder_by_default = fields.Selection([
        ('nominatim_openfire', "OpenFire"),
        ('nominatim_osm', "OpenStreetMap"),
        ('bano', u"Base Adresse Nationale Ouverte (BANO)"),
        ('google_maps', "Google Maps")], u"Géocodeur fonctions automatiques", default=_get_default_geocoder_by_default,
        help=u"Géocodeur par défaut pour fonctions automatiques")

    # Save fields
    # URLs
    @api.multi
    def set_url_openfire(self):
        self.ensure_one()
        value = getattr(self, 'url_openfire', '')
        self.env['ir.config_parameter'].set_param('url_openfire', value)

    @api.multi
    def set_url_osm(self):
        self.ensure_one()
        value = getattr(self, 'url_osm', '')
        self.env['ir.config_parameter'].set_param('url_osm', value)

    @api.multi
    def set_url_bano(self):
        self.ensure_one()
        value = getattr(self, 'url_bano', '')
        self.env['ir.config_parameter'].set_param('url_bano', value)

    @api.multi
    def set_url_google(self):
        self.ensure_one()
        value = getattr(self, 'url_google', '')
        self.env['ir.config_parameter'].set_param('url_google', value)

    # Google API key
    @api.multi
    def set_google_api_key(self):
        self.ensure_one()
        value = getattr(self, 'google_api_key', '')
        self.env['ir.config_parameter'].set_param('google_api_key', value)

    # Automatics functions
    @api.multi
    def set_show_stats(self):
        self.ensure_one()
        value = getattr(self, 'show_stats', '')
        self.env['ir.config_parameter'].set_param('show_stats', value)

    @api.multi
    def set_geocoding_on_write(self):
        self.ensure_one()
        value = getattr(self, 'geocoding_on_write', '')
        self.env['ir.config_parameter'].set_param('geocoding_on_write', value)

    @api.multi
    def set_geocoding_on_create(self):
        self.ensure_one()
        value = getattr(self, 'geocoding_on_create', '')
        self.env['ir.config_parameter'].set_param('geocoding_on_create', value)

    @api.multi
    def set_geocoder_by_default(self):
        self.ensure_one()
        value = getattr(self, 'geocoder_by_default', '')
        self.env['ir.config_parameter'].set_param('geocoder_by_default', value)
