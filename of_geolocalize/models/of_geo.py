# -*- coding: utf-8 -*-

from odoo import api, fields, models

GEO_PRECISION = [
    ('manual', "Manuel"),
    ('very_high', "Excellent"),
    ('high', "Haut"),
    ('medium', "Moyen"),
    ('low', "Bas"),
    ('no_address', u"--"),
    ('unknown', u"Indéterminé"),
    ('not_tried', u"Pas tenté"),
]


# Add geocoding fields to res.company model (all are related to partner_id)
class ResCompany(models.Model):
    _inherit = "res.company"

    geo_lat = fields.Float(string='Geo Lat', digits=(8, 8), related='partner_id.geo_lat', help="latitude field")
    geo_lng = fields.Float(string='Geo Lng', digits=(8, 8), related='partner_id.geo_lng', help="longitude field")
    date_last_localization = fields.Datetime(
        string='Last Geolocation Date', related='partner_id.date_last_localization', readonly=True)
    geocoding_response = fields.Text(
        string=u"Réponse géocadage", related='partner_id.geocoding_response', readonly=True)
    geocoding = fields.Selection(
        [
            ('not_tried', u"Pas tenté"),
            ('no_address', u"--"),
            ('success_openfire', u"Réussi"),
            ('success_osm', u"Réussi"),
            ('success_bano', u"Réussi"),
            ('success_google', u"Réussi"),
            ('success_mapbox', u"Réussi"),
            ('need_verif', u"Nécessite vérification"),
            ('failure', u"Échoué"),
            ('manual', u"Manuel"),
        ], default='not_tried', readonly=True, help="field defining the state of the geocoding for this partner",
        related='partner_id.geocoding')
    geocodeur = fields.Selection(
        [
            ('nominatim_openfire', u"OpenFire"),
            ('nominatim_osm', u"OpenStreetMap"),
            ('bano', u"BANO"),
            ('google_maps', u"Google Maps"),
            ('mapbox', u"MapBox"),
            ('manual', u"Manuel"),
            ('unknown', u"Indéterminé"),
        ], default='unknown', readonly=True, related='partner_id.geocodeur',
        help=u"Champ définissant le géocodeur utilisé")
    precision = fields.Selection(
        GEO_PRECISION, default='not_tried', readonly=True, related='partner_id.precision',
        help=u"Niveau de précision de la géolocalisation.\n"
             u"bas: à la ville.\n"
             u"moyen: au village\n"
             u"haut: à la rue / au voisinage\n"
             u"très haut: au numéro de rue\n")
    street_query = fields.Char(string=u"Adresse requête", related='partner_id.street_query', readonly=True)


# Add geocoding parameters to res.partner model
class ResPartner(models.Model):
    _inherit = "res.partner"

    geo_lat = fields.Float(
        string='Geo Lat', digits=(8, 8), group_operator=False, help="latitude field", track_visibility="onchange")
    geo_lng = fields.Float(
        string='Geo Lng', digits=(8, 8), group_operator=False, help="longitude field", track_visibility="onchange")
    date_last_localization = fields.Datetime(string='Last Geolocation Date', readonly=True)
    geocoding_response = fields.Text(string=u"Réponse géocodage", readonly=True)
    geocoding = fields.Selection(
        [
            ('not_tried', u"Pas tenté"),
            ('no_address', u"--"),
            ('success_openfire', u"Réussi"),
            ('success_osm', u"Réussi"),
            ('success_bano', u"Réussi"),
            ('success_google', u"Réussi"),
            ('success_mapbox', u"Réussi"),
            ('need_verif', u"Nécessite vérification"),
            ('failure', u"Échoué"),
            ('manual', u"Manuel"),
        ], default='not_tried', readonly=True, help="field defining the state of the geocoding for this partner",
        required=True)
    geocodeur = fields.Selection(
        [
            ('nominatim_openfire', u"OpenFire"),
            ('nominatim_osm', u"OpenStreetMap"),
            ('bano', u"BANO"),
            ('google_maps', u"Google Maps"),
            ('mapbox', u"MapBox"),
            ('manual', u"Manuel"),
            ('unknown', u"Indéterminé"),
        ], default='unknown', readonly=True, help=u"Champ définissant le géocodeur utilisé")
    precision = fields.Selection(
        GEO_PRECISION, default='not_tried', readonly=True, help=u"Niveau de précision de la géolocalisation.\n"
                                                                u"bas: à la ville.\n"
                                                                u"moyen: au village\n"
                                                                u"haut: à la rue / au voisinage\n"
                                                                u"très haut: au numéro de rue\n")
    street_query = fields.Char(string=u"Adresse requête")
    street_response = fields.Char(string=u"Adresse réponse", readonly=True)

    @api.multi
    def button_verify_geocoding(self):
        self.ensure_one()
        if self.geocodeur == 'bano':
            self.geocoding = 'success_bano'
        elif self.geocodeur == 'mapbox':
            self.geocoding = 'success_mapbox'
        return True

    @api.multi
    def button_refute_geocoding(self):
        self.ensure_one()
        self.geocoding = 'failure'
        self.geo_lat = 0
        self.geo_lng = 0
        self.precision = 'unknown'
        return True

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
            '%s %s' % (self.zip or '', self.city or ''),
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
        geocode_func = {
            'bano': geo_obj.geo_ban,
            'mapbox': geo_obj.geo_mapbox,
        }
        for partner in self:
            if partner.country_id.code != 'FR':
                geocode = geocode_func['mapbox']
            else:
                geocode = geocode_func.get(geocodeur, geo_obj.geo_ban)
            results = geocode(partner)
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
                partner.geo_code()
        return partner

    # Conditional writing when partner address or GPS coordinates are modified
    @api.multi
    def write(self, vals):
        # Get config paramenter geocoding on write
        res_geocoding_on_write = self.env['ir.config_parameter'].get_param('geocoding_on_write') == 'yes'

        # Partenaires à géocoder.
        to_update = self.env['res.partner']

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
            for partner in self:
                for key in ('street', 'street2', 'zip', 'city'):
                    # au moins un champ d'adresse a effectivement été modifié
                    if key in vals and partner[key] != vals[key]:
                        to_update |= partner
                        break
                else:
                    # Champs M2O
                    for key in ('state_id', 'country_id'):
                        if key in vals and partner[key].id != vals[key]:
                            to_update |= partner
                            break

        result = super(ResPartner, self).write(vals)

        # DO GEOCODING AUTOMATIC (through wizard)
        if to_update:
            if res_geocoding_on_write:  # Do geocoding automatic
                to_update.geo_code()
            else:  # if config gecoding on write False, set as not tried
                vals = {
                    'geocoding': 'not_tried',
                    'geocodeur': 'unknown',
                    'geo_lat': 0,
                    'geo_lng': 0,
                    'precision': 'not_tried',
                    'date_last_localization': fields.Datetime.context_timestamp(self, fields.datetime.now()),
                }
                to_update.write(vals)
        return result


# Configuration
class OFGeoConfiguration(models.TransientModel):
    _name = 'of.geo.config.settings'
    _inherit = 'res.config.settings'

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

    show_stats = fields.Boolean(string=u'Afficher stats', default=_get_default_show_stats)
    geocoding_on_write = fields.Selection(
        [
            ('no', u"Ne pas recalculer les valeurs du géocodage automatiquement "
                   u"(Les coordonnées GPS sont remises à zéro si elles ne sont pas entrées en même temps.)"),
            ('yes', u"Recalculer les valeurs de géocodage (Le géocodage est tenté si les coordonnées GPS ne sont pas entrées en même temps.)"),
        ], u"Si une adresse est modifiée", default=_get_default_geocoding_on_write,
        help=u"Recalculer automatiquement les valeurs de géocodage lorsque l'adresse d'un partenaire est modifiée")
    geocoding_on_create = fields.Selection(
        [
            ('no', u"Ne pas calculer les valeurs de géocodage "
                   u"(recommandé lorsqu'un grand nombre de partenaires sont importés)"),
            ('yes', u"Calculer les valeurs de géocodage automatiquement"),
        ], u"Si un partenaire est ajouté", default=_get_default_geocoding_on_create,
        help=u"Calculer automatiquement les valeurs de géocodage lorsqu'un nouveau partenaire est ajouté")
    geocoder_by_default = fields.Selection(
        [
            ('mapbox', "MapBox"),
            ('bano', u"Base Adresse Nationale Ouverte (BANO)"),
        ], u"Géocodeur fonctions automatiques", default=_get_default_geocoder_by_default,
        help=u"Géocodeur par défaut pour fonctions automatiques")

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
