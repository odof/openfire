# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import logging
import json
import pytz
from datetime import datetime, timedelta
from collections import OrderedDict

from odoo import http, tools, fields
from odoo.http import request
from odoo.exceptions import ValidationError
from odoo.tools.float_utils import float_compare
from odoo.addons.of_utils.models.of_utils import hours_to_strs
from odoo.addons.website_portal.controllers.main import website_account

_logger = logging.getLogger(__name__)

STEP_NAME_NUMBER = {
    'new': 0,
    'installed_park_select': 10,
    'installed_park_create': 10,
    'adresse': 20,
    'address_select': 20,
    'address_edit': 25,
    'localize': 30,
    'service': 40,
    'slot': 50,
    'confirmation': 60,
    'thank_you': 70,
}


class WebsiteAccount(website_account):

    def _prepare_portal_layout_values(self):
        values = super(WebsiteAccount, self)._prepare_portal_layout_values()
        values.update({
            'installed_park_count': request.env.user.partner_id.of_parc_installe_count,
        })
        return values

    @http.route(['/my/of_installed_parks'], type='http', auth='user', website=True)
    def portal_my_of_installed_parks(self):
        values = self._prepare_portal_layout_values()
        values.update({
            'partner': request.env.user.partner_id,
            'installed_parks': request.env.user.partner_id.of_parc_installe_ids,
        })
        return request.render(
            'of_website_planning_booking.of_website_planning_booking_portal_my_home_of_installed_parks', values)


class OFWebsitePlanningBooking(http.Controller):

    def get_redirection(self, step):
        # L'utilisateur n'est pas connecté -> on le redirige sur la page de connexion
        if request.env.uid == request.website.user_id.id:
            return request.redirect('/web/login')
        step_number = STEP_NAME_NUMBER[step] or 0
        # À ce stade, le partenaire est nécessaire
        if step_number > 0 and not request.session.get('booking_partner_id'):
            return request.redirect('/new_booking')
        partner = request.env['res.partner'].sudo().browse(request.session.get('booking_partner_id'))
        # Si le partenaire n'a pas de parc installé, on le redirige directement sur la page de création de
        # parc installé si l'option est activé ou vers la page d'inposibilité
        if step == 'installed_park_select' and not partner.of_parc_installe_ids:
            if request.env.user.has_group('of_website_planning_booking.group_website_booking_allow_park_creation'):
                return request.redirect('/new_booking/installed_park_create')
            else:
                values = {'message': u"Nous ne parvenons pas à identifier votre équipement, veuillez contacter votre "
                                     u"magasin au %s." % request.env.user.partner_id.company_id.phone}
                return request.render('of_website_planning_booking.new_booking_sorry', values)
        # Si le partenaire n'a pas d'adresse, on le redirige directement vers la création d'adresse
        if step == 'address_select' and not partner.street:
            request.params['mode'] = 'new'
            return request.redirect('/new_booking/address_create_edit')
        # À ce stade, le parc installé est nécessaire
        if step_number >= 20 and not request.session.get('booking_parc_installe_id'):
            return request.redirect('/new_booking/installed_park_select')
        # À ce stade, l'adresse est nécessaire
        if step_number >= 30 and not request.session.get('rdv_site_adresse_id'):
            return request.redirect('/new_booking/address_select')
        # À ce stade, l'adresse est nécessaire
        if step_number >= 50 and \
                not (request.session.get('rdv_tache_id') and request.session.get('rdv_date_recherche_debut')):
            return request.redirect('/new_booking/service')
        # À ce stade, un créneau web doit avoir été sélectionné
        if step_number >= 60:
            if not request.session.get('rdv_creneau_id'):
                return request.redirect('/new_booking/slot')
            creneau_obj = request.env['of.tournee.rdv.line.website'].sudo()
            # Le cron d'épuration des transients a supprimé l'enregistrement -> retour à la sélection de prestation
            if not creneau_obj.browse(request.session['rdv_creneau_id']).exists():
                request.session['rdv_search_wiz_id'] = False
                return request.redirect('/new_booking/service')
        return False

    @http.route(['/new_booking'], type='http', auth='user', website=True)
    def new_booking(self, **kw):
        redirection = self.get_redirection('new')
        if redirection:
            return redirection

        # Valeurs de session nécessaires au passage à l'étape suivante
        request.session['booking_partner_id'] = request.env.user.partner_id.id

        return request.redirect('/new_booking/installed_park_select')

    @http.route(['/new_booking/installed_park_select'], type='http', auth='user', website=True)
    def new_booking_installed_park_select(self, **kw):
        current_step = 'installed_park_select'

        # Retour en arrière si les informations nécessaires ne sont pas présentes dans la session
        redirection = self.get_redirection(current_step)
        if redirection:
            return redirection

        values = kw
        error = dict()
        validated = False

        # Le formulaire de l'étape sélection d'équipement a été soumis -> traitement
        if 'submitted' in values:
            values.pop('submitted')
            if not values.get('parc_installe_id') and not values.get('create'):
                error['parc_installe_id'] = True
            else:
                validated = True

        values['error_dict'] = error

        if validated:
            if values.get('create'):
                # On redirige vers le formulaire de création de parc installé
                request.session.pop('booking_parc_installe_id', None)
                return request.redirect('/new_booking/installed_park_create')
            request.session['booking_parc_installe_id'] = int(values['parc_installe_id'])
            if values.get('update'):
                # On redirige vers le formulaire de MAJ du parc installé
                return request.redirect('/new_booking/installed_park_create')
            # Passage à l'étape sélection d'adresse
            # Supprimer la valeur d'adresse stockée en session (en cas de retour et changement de parc installé)
            request.session['site_adresse_id'] = False
            return request.redirect('/new_booking/address_select')

        # Arrivée sur la page ou erreur intermédiaire
        values['step_number'] = STEP_NAME_NUMBER.get(current_step, 'new')
        values['parc_installe_list'] = request.env.user.partner_id.of_parc_installe_ids

        if values.get('parc_installe_list'):
            # Si la session a déjà un parc installé. Exemple clic sur 'retour' à l'étape adresse
            values['parc_installe_id'] = request.session.get('booking_parc_installe_id')

        # Création d'un parc installé extérieur
        if request.env.user.has_group('of_website_planning_booking.group_website_booking_allow_park_creation'):
            values['display_add_button'] = True

        return request.render('of_website_planning_booking.new_booking_installed_park_select', values)

    @http.route(['/new_booking/installed_park_create'], type='http', auth='user', website=True)
    def new_booking_installed_park_create(self, **kw):
        current_step = 'installed_park_create'

        # Retour en arrière si les informations nécessaires ne sont pas présentes dans la session
        redirection = self.get_redirection(current_step)
        if redirection:
            return redirection

        values = kw
        error = dict()
        validated = False
        create = True
        if request.session.get('booking_parc_installe_id'):
            create = False

        # Le formulaire de l'étape sélection d'équipement a été soumis -> traitement
        if 'submitted' in values:
            values.pop('submitted')
            # Champs obligatoires
            if not values.get('product_category_id'):
                error['product_category_id'] = True
            if not values.get('brand_id'):
                error['brand_id'] = True
            elif values.get('brand_id') == 'Autre marque' and not values.get('extra_brand'):
                error['extra_brand'] = True
            if not values.get('modele'):
                error['modele'] = True
            # Validation de champs
            error_message = []
            # Vérifier la longueur des champs
            if values.get('extra_brand') and len(values['extra_brand']) > 100:
                error['extra_brand'] = True
                error_message.append(u"Le champ 'Autre' ne doit pas dépasser 100 caractères.")
            if values.get('modele') and len(values['modele']) > 100:
                error['modele'] = True
                error_message.append(u"Le champ 'Modèle' ne doit pas dépasser 100 caractères.")
            if values.get('name') and len(values['name']) > 100:
                error['name'] = True
                error_message.append(u"Le champ 'N° de série' ne doit pas dépasser 100 caractères.")
            if values.get('type_conduit') and len(values['type_conduit']) > 100:
                error['type_conduit'] = True
                error_message.append(u"Le champ 'Type de conduit' ne doit pas dépasser 100 caractères.")
            if values.get('installateur_name') and len(values['installateur_name']) > 100:
                error['installateur_name'] = True
                error_message.append(u"Le champ 'Nom de l'installateur' ne doit pas dépasser 100 caractères.")
            if values.get('installateur_email') and len(values['installateur_email']) > 100:
                error['installateur_email'] = True
                error_message.append(u"Le champ 'E-mail de l'installateur' ne doit pas dépasser 100 caractères.")
            # Contrôle de la date
            if values.get('date_installation'):
                try:
                    fields.Date.from_string(values['date_installation'])
                    if not ('1900-01-01' < values['date_installation'] < '3000-01-01'):
                        error['date_installation'] = True
                        error_message.append(u"La date d'installation doit être comprise entre le 01/01/1900 "
                                             u"et le 01/01/3000")
                except ValueError:
                    error['date_installation'] = True
                    error_message.append(u"La date d'installation indiquée ne correspond pas à une date valide.")
            # Contrôle de l'année de construction
            if values.get('annee_batiment'):
                if len(values['annee_batiment']) != 4 or any(not i.isdigit() for i in values['annee_batiment']):
                    error['annee_batiment'] = True
                    error_message.append(u"L'année de construction du batîment ne correspond pas à une année valide.")
            # Contrôle de l'unicité du numéro de série dans la base
            if create and values.get('name') and request.env['of.parc.installe'].sudo().search(
                    [('name', '=', values.get('name'))], limit=1) or not create and values.get('name') and \
                    request.env['of.parc.installe'].sudo().search(
                        [('name', '=', values.get('name')),
                         ('id', '!=', int(request.session.get('booking_parc_installe_id')))]):
                error['name'] = True
                error_message.append(u"Ce numéro de série existe déjà dans notre logiciel,"
                                     u" veuillez vérifier sa valeur et contacter le service client si besoin.")
            if error:
                error['error_message'] = error_message
            else:
                validated = True

        values['error_dict'] = error

        if validated:
            if create:
                parc_installe = self._create_parc_installe()
                request.session['booking_parc_installe_id'] = parc_installe.id
            else:
                self._update_parc_installe(int(request.session['booking_parc_installe_id']))
            # Passage à l'étape sélection d'adresse
            # Supprimer la valeur d'adresse stockée en session (en cas de retour et changement de parc installé)
            request.session['site_adresse_id'] = False
            return request.redirect('/new_booking/address_select')

        # Arrivée sur la page ou erreur intermédiaire
        values['step_number'] = STEP_NAME_NUMBER.get(current_step, 'new')
        parc_installe_obj = request.env['of.parc.installe']
        parc_installe = parc_installe_obj

        # En mode MAJ, on charge les infos du parc installé
        if request.session.get('booking_parc_installe_id'):
            parc_installe = parc_installe_obj.browse(request.session.get('booking_parc_installe_id'))

        values['product_categ_list'] = request.env['product.category']\
            .search([('of_website_planning_published', '=', True)])
        values['brand_list'] = request.env['of.product.brand'].search([('of_website_planning_published', '=', True)])
        values['product_category'] = 'product_category_id' in values and values['product_category_id'] != '' and \
                                     request.env['product.category'].browse(int(values['product_category_id'])) or \
                                     parc_installe.product_category_id
        other_brand_id = request.env['ir.values'].sudo().get_default(
            'of.intervention.settings', 'website_booking_default_product_brand_id')
        values['brand'] = 'brand_id' in values and values['brand_id'] != '' and values['brand_id'] != 'Autre marque' \
                          and request.env['of.product.brand'].browse(int(values['brand_id'])) or parc_installe.brand_id
        values['brand_id'] = values.get('brand_id') or parc_installe.brand_id.id == other_brand_id and 'Autre marque'
        values['extra_brand'] = values.get('extra_brand') or parc_installe.brand_id.id == other_brand_id and \
            parc_installe.website_extra_brand
        values['modele'] = values.get('modele') or parc_installe.modele
        values['name'] = values.get('name') or parc_installe.name
        values['type_conduit'] = values.get('type_conduit') or parc_installe.type_conduit
        values['date_installation'] = values.get('date_installation') or parc_installe.date_installation
        values['annee_batiment'] = values.get('annee_batiment') or parc_installe.annee_batiment
        values['installateur_name'] = values.get('installateur_name') or parc_installe.website_installer_name
        values['installateur_email'] = values.get('installateur_email') or parc_installe.website_installer_email

        # Autoriser les marques extérieures
        if request.env.user.has_group('of_website_planning_booking.group_website_booking_allow_park_brand_creation'):
            values['display_extra_brand'] = True

        return request.render('of_website_planning_booking.new_booking_installed_park_create', values)

    @http.route(['/new_booking/address_select'], type='http', auth='user', website=True)
    def new_booking_address_select(self, **kw):
        current_step = 'address_select'

        # Retour en arrière si les informations nécessaires ne sont pas présentes dans la session
        redirection = self.get_redirection(current_step)
        if redirection:
            return redirection

        values = kw

        # Le formulaire de l'étape sélection d'adresse a été soumis -> traitement
        if 'submitted' in values:
            # On contrôle le secteur
            address = request.env['res.partner'].browse(request.session.get('rdv_site_adresse_id'))
            if not address.of_secteur_tech_id:
                # On tente d'assigner un secteur
                secteur = request.env['of.secteur'].sudo().get_secteur_from_cp(address.zip).filtered(
                    lambda sec: sec.type in ('tech', 'tech_com'))
                if not secteur:
                    values = {
                        'return_button': True,
                        'return_button_href': '/new_booking/address_select',
                        'message': u"Nous ne sommes pas en mesure d'intervenir à cette adresse, veuillez contacter "
                                   u"votre magasin au %s." % request.env.user.partner_id.company_id.phone}
                    return request.render('of_website_planning_booking.new_booking_sorry', values)
                else:
                    address.sudo().of_secteur_tech_id = secteur
            return request.redirect('/new_booking/localize')

        # Une adresse différente a été sélectionnée -> pas de nouveau rendu mais màj session
        if values.get('site_adresse_id') and values.get('xhr'):
            request.session['rdv_site_adresse_id'] = int(values['site_adresse_id'])
            return 'ok'

        # Arrivée sur la page ou erreur intermédiaire
        values['step_number'] = STEP_NAME_NUMBER.get(current_step, 'new')

        parc_installe_id = request.session.get('booking_parc_installe_id')
        parc_installe = request.env['of.parc.installe'].browse(parc_installe_id)
        partner = request.env.user.partner_id
        # Le parc installé n'a pas d'adresse enregistrée -> on laisse le choix
        if not parc_installe.site_adresse_id:
            adresse_list = request.env['res.partner'].search([('id', 'child_of', partner.commercial_partner_id.id)])
        else:
            adresse_list = parc_installe.site_adresse_id
        if request.session.get('rdv_site_adresse_id') and \
                request.session.get('rdv_site_adresse_id') not in adresse_list.ids:
            request.session['rdv_site_adresse_id'] = False

        values['adresse_list'] = adresse_list
        values['parc_installe'] = parc_installe
        values['site_adresse_id'] = request.session.get('rdv_site_adresse_id') or \
            parc_installe.site_adresse_id.id or parc_installe.client_id.id
        request.session['rdv_site_adresse_id'] = values['site_adresse_id']

        return request.render('of_website_planning_booking.new_booking_address_select', values)

    @http.route(['/new_booking/address_create_edit'], type='http', auth='user', website=True)
    def new_booking_address_create_edit(self, **kw):
        current_step = 'address_edit'

        # Retour en arrière si les informations nécessaires ne sont pas présentes dans la session
        redirection = self.get_redirection(current_step)
        if redirection:
            return redirection

        values = kw
        error = dict()
        validated = False

        # Le formulaire de l'étape création / édition d'adresse a été soumis -> traitement
        if 'submitted' in values:
            values.pop('submitted')
            # Champs obligatoires
            # Pour l'adresse principale : le nom, le téléphone et l'email sont obligatoires
            if values.get('adresse_principale'):
                if not values.get('name'):
                    error['name'] = True
                if not values.get('email'):
                    error['email'] = True
                if not values.get('phone'):
                    error['phone'] = True
            # Pour toutes les adresses : la rue, le code postal, la ville et le pays sont obligatoires
            if not values.get('street'):
                error['street'] = True
            if not values.get('zip'):
                error['zip'] = True
            if not values.get('city'):
                error['city'] = True
            if not values.get('country_id'):
                error['country_id'] = True

            if not error:
                validated = True

        values['error_dict'] = error

        if validated:
            if values.get('mode') == 'first':
                site_adresse_id = request.session.get('booking_partner_id')
            elif values.get('mode') == 'edit':
                site_adresse_id = request.session.get('rdv_site_adresse_id')
            else:
                site_adresse_id = False
            if site_adresse_id:
                self._update_address_if_necessary(int(site_adresse_id))
            else:
                site_address_id = self._create_new_address(request.session.get('booking_partner_id'))
                request.session['rdv_site_adresse_id'] = site_address_id
            return request.redirect('/new_booking/address_select')

        # Arrivée sur la page ou erreur intermédiaire
        values['step_number'] = STEP_NAME_NUMBER.get(current_step, 'new')

        # Première adresse -> values vide
        # Nouvelle adresse -> 'mode': 'new' dans values
        # Modif adresse -> 'site_adresse_id' dans values
        mode = values.get('mode', values.get('site_adresse_id') and 'edit' or 'first')
        values['mode'] = mode
        partner_obj = request.env['res.partner']
        partner = partner_obj
        if mode == 'first':
            partner = request.env.user.partner_id
            values['adresse_principale'] = True
        elif mode == 'new':
            values['adresse_principale'] = False
        elif mode == 'edit':
            request.session['rdv_site_adresse_id'] = values['site_adresse_id']
            partner = partner_obj.browse(int(values['site_adresse_id']))
            if partner.id == request.env.user.partner_id.id:
                values['adresse_principale'] = True
            else:
                values['adresse_principale'] = False

        values['partner'] = partner
        values['name'] = values.get('name') or partner.name
        values['email'] = values.get('email') or partner.email
        values['phone'] = values.get('phone') or partner.phone
        values['street'] = values.get('street') or partner.street
        values['street2'] = values.get('street2') or partner.street2
        values['zip_code'] = values.get('zip') or partner.zip
        values['city'] = values.get('city') or partner.city
        values['country'] = values.get('country_id') and request.env['res.country'].browse(int(values['country_id'])) \
            or partner.country_id or request.env['res.country'].search([('name', '=', u"France")], limit=1)
        values['country_list'] = request.env['res.country'].search([])

        return request.render('of_website_planning_booking.new_booking_address_create_edit', values)

    @http.route(['/new_booking/localize'], type='http', auth='user', website=True)
    def new_booking_localize(self, **kw):
        current_step = 'localize'

        # Retour en arrière si les informations nécessaires ne sont pas présentes dans la session
        redirection = self.get_redirection(current_step)
        if redirection:
            return redirection

        values = kw

        # Le formulaire de l'étape localisation a été rempli -> traitement et passage à l'étape créneau
        if 'submitted' in values:
            self._update_geo_info()
            return request.redirect('/new_booking/service')

        # Arrivée sur la page ou erreur intermédiaire
        values['step_number'] = STEP_NAME_NUMBER.get(current_step, 'new')

        try:
            google_maps_api_key = request.env['ir.config_parameter'].sudo().get_param('google_maps_api_key', '')
            map_lat_lng = []
            partner = request.env['res.partner'].browse(request.session.get('rdv_site_adresse_id'))
            map_lat_lng.append({'name': partner.name, 'geo_lat': partner.geo_lat, 'geo_lng': partner.geo_lng, })
        except Exception, e:
            _logger.error(
                u"Erreur lors de l'affichage de la carte de l'adresse d'installation : %s" % tools.ustr(e))
            return request.render("website.403")

        values.update({
            'googleAPIKey': google_maps_api_key,
            'map_lat_lng': json.dumps(map_lat_lng),
            'geo_lat': values.get('geo_lat', partner.geo_lat),
            'geo_lng': values.get('geo_lng', partner.geo_lng),
            'of_geo_comment': partner.of_geo_comment,
        })

        return request.render('of_website_planning_booking.new_booking_localize', values)

    @http.route(['/new_booking/service'], type='http', auth='user', website=True)
    def new_booking_service(self, **kw):
        current_step = 'service'

        # Retour en arrière si les informations nécessaires ne sont pas présentes dans la session
        redirection = self.get_redirection(current_step)
        if redirection:
            return redirection

        values = kw
        error = dict()
        validated = False

        # Le formulaire de l'étape localisation a été soumis -> traitement
        if 'submitted' in values:
            values.pop('submitted')
            error_message = []
            # Champs obligatoires
            if not values.get('tache_id'):
                error['tache_id'] = True
            if not values.get('date_recherche_debut'):
                error['date_recherche_debut'] = True
            else:
                # Validation de la date
                search_date = fields.Date.from_string(values.get('date_recherche_debut'))
                # La date de début de recherche doit être dans le futur
                if search_date <= fields.Date.from_string(fields.Date.today()):
                    error['date_recherche_debut'] = True
                    error_message.append(u"La date de début de recherche doit être future.")
                # La date de début doit être inférieur au paramètre de configuration
                max_days = request.env['ir.values'].sudo().get_default(
                    'of.intervention.settings', 'website_booking_open_days_number')
                max_search_date = fields.Date.from_string(fields.Date.today()) + timedelta(days=max_days)
                if search_date > max_search_date:
                    error['date_recherche_debut'] = True
                    error_message.append(
                        u"La date de début de recherche ne doit pas être à plus de %d jours." % max_days)

            if error:
                error['error_message'] = error_message
            else:
                validated = True

        values['error_dict'] = error

        if validated:
            request.session['rdv_tache_id'] = int(values['tache_id'])
            request.session['rdv_date_recherche_debut'] = values['date_recherche_debut']
            # Marquer pour une nouvelle recherche. les perfs pourraient être améliorées en vérifiant
            # si l'adresse / la prestation / la date a effectivement changé depuis la denière recherche
            # (en cas de retour a une étape précédente par exemple)
            request.session['rdv_search_wiz_id'] = False
            request.session['rdv_creneau_id'] = False
            return request.redirect('/new_booking/slot')

        # Arrivée sur la page ou erreur intermédiaire
        values['step_number'] = STEP_NAME_NUMBER.get(current_step, 'new')
        values['tache_list'] = request.env['of.planning.tache'].search([])

        # Si la session a déjà une tâche. Exemple clic sur 'retour' à l'étape creneau
        if not values.get('tache_id') and request.session.get('rdv_tache_id'):
            values['tache'] = request.env['of.planning.tache'].browse(request.session.get('rdv_tache_id'))
        else:
            values['tache'] = 'tache_id' in values and values['tache_id'] != '' and \
                              request.env['of.planning.tache'].browse(int(values['tache_id']))

        # Si la session a déjà une date. Exemple clic sur 'retour' à l'étape creneau
        if not values.get('date_recherche_debut') and request.session.get('rdv_date_recherche_debut'):
            values['date_recherche_debut'] = request.session.get('rdv_date_recherche_debut')

        return request.render('of_website_planning_booking.new_booking_service', values)

    @http.route(['/new_booking/slot'], type='http', auth='user', website=True)
    def new_booking_slot(self, **kw):
        current_step = 'slot'

        # Retour en arrière si les informations nécessaires ne sont pas présentes dans la session
        redirection = self.get_redirection(current_step)
        if redirection:
            return redirection

        values = kw

        # Un créneau différent vient d'être sélectionné
        if values.get('creneau_id') and values.get('xhr'):
            creneau_id = int(values['creneau_id'])
            request.session['rdv_creneau_id'] = creneau_id
            creneau = request.env['of.tournee.rdv.line.website'].browse(creneau_id).exists()
            creneau.button_select(sudo=True)
            return 'ok'

        # Arrivée sur la page
        values['step_number'] = STEP_NAME_NUMBER.get(current_step, 'new')

        # Recherche de créneaux
        mode = request.env['ir.values'].sudo().get_default('of.intervention.settings', 'website_booking_slot_size')
        compute = ''

        # Wizard de recherche
        if not (request.session.get('rdv_search_wiz_id') and request.session.get('rdv_creneau_id')):
            # Il faut générer un nouveau wizard de recherche
            tache = request.env['of.planning.tache'].browse(request.session.get('rdv_tache_id'))
            wizard_vals = {
                'company_id': request.website.company_id.id,
                'partner_id': request.env.user.partner_id.id,
                'partner_address_id': request.session.get('rdv_site_adresse_id'),
                'tache_id': request.session.get('rdv_tache_id'),
                'date_recherche_debut': request.session.get('rdv_date_recherche_debut'),
                'duree': tache.duree,
                'ignorer_geo': True,
            }
            search_wizard = request.env['of.tournee.rdv'].create(wizard_vals)
            search_wizard._onchange_date_recherche_debut()
            search_wizard._onchange_mode_recherche()
            request.session['rdv_search_wiz_id'] = search_wizard.id
            request.session['rdv_creneau_id'] = False
            compute = 'new'
            request.session['search_slot_result_nb'] = 10
        else:
            # Récupération du wizard existant
            search_wizard_id = request.session.get('rdv_search_wiz_id')
            search_wizard = request.env['of.tournee.rdv'].browse(search_wizard_id).exists()
            # Le cron de purge des transients a supprimé l'enregistrement
            if not search_wizard:
                request.session['rdv_creneau_id'] = False
                request.session['rdv_search_wiz_id'] = False
                return request.redirect('/new_booking/slot')
            # Clic sur le bouton "Chercher plus"
            if values.get('submitted') and values.get('load_more'):
                new_search_start_date = fields.Date.from_string(search_wizard.date_recherche_fin) + timedelta(days=1)
                new_search_end_date = new_search_start_date + timedelta(days=6)
                search_wizard.date_recherche_debut = fields.Date.to_string(new_search_start_date)
                search_wizard.date_recherche_fin = fields.Date.to_string(new_search_end_date)
                compute = 'more'
                request.session['search_slot_result_nb'] += 5
            else:
                request.session['search_slot_result_nb'] = 10

        # Lancement de la recherche
        if compute:
            address = request.env['res.partner'].browse(request.session.get('rdv_site_adresse_id'))

            # Nombre de jours max ouverts à la réservation
            max_days = request.env['ir.values'].sudo().get_default(
                'of.intervention.settings', 'website_booking_open_days_number')
            max_search_date = fields.Date.from_string(request.session.get('rdv_date_recherche_debut')) + \
                timedelta(days=max_days)
            max_search_date = fields.Date.to_string(max_search_date)
            search_wizard.date_recherche_fin = min(search_wizard.date_recherche_fin, max_search_date)
            search_wizard.compute(sudo=True, mode=compute, secteur_id=address.of_secteur_tech_id.id, web=True)

            # Tenter jusqu'à avoir au moins 10 résultats ou ne plus être dans les jours ouverts à la réservation
            while len(search_wizard.planning_ids.filtered(lambda p: p.disponible)) < \
                    request.session['search_slot_result_nb'] and search_wizard.date_recherche_fin < max_search_date:
                new_search_start_date = fields.Date.from_string(search_wizard.date_recherche_fin) + timedelta(days=1)
                new_search_end_date = new_search_start_date + timedelta(days=6)
                search_wizard.date_recherche_debut = fields.Date.to_string(new_search_start_date)
                search_wizard.date_recherche_fin = fields.Date.to_string(new_search_end_date)
                search_wizard.date_recherche_fin = min(search_wizard.date_recherche_fin, max_search_date)
                search_wizard.compute(sudo=True, mode='more', secteur_id=address.of_secteur_tech_id.id, web=True)

            if search_wizard.planning_ids.filtered(lambda p: p.disponible):
                creneaux_web = search_wizard.build_website_creneaux(mode=mode)
                creneaux_web = creneaux_web[0:request.session['search_slot_result_nb']]
                if creneaux_web:
                    creneau_selected = creneaux_web[0]
                    request.session['rdv_creneau_id'] = creneau_selected.id
                else:
                    creneau_selected = False
            else:
                creneaux_web = []
                creneau_selected = False

            if search_wizard.date_recherche_fin == max_search_date:
                values['nomore_load'] = True
        else:
            creneaux_web = search_wizard.website_creneaux_ids
            creneaux_web = creneaux_web[0:request.session['search_slot_result_nb']]
            creneau_selected = request.env['of.tournee.rdv.line.website'].browse(request.session.get('rdv_creneau_id'))

        # On s'assure qu'il y ait un seul créneau sélectionné, en cas de raifraichissement de page après bouton
        # "chercher plus" par exemple
        if creneau_selected and creneau_selected.exists():
            creneau_selected.button_select(sudo=True)
        else:
            values = {
                'return_button': True,
                'return_button_href': '/new_booking/service',
                'message': u"Aucun créneau libre ne correspond à votre recherche, veuillez contacter "
                           u"votre magasin au %s." % request.env.user.partner_id.company_id.phone}
            return request.render('of_website_planning_booking.new_booking_sorry', values)

        if request.session['search_slot_result_nb'] >= 20:
            values['nomore_load'] = True

        values['creneaux'] = creneaux_web
        values['creneau_selected'] = creneau_selected

        return request.render('of_website_planning_booking.new_booking_slot', values)

    @http.route(['/new_booking/confirmation'], type='http', auth='user', website=True)
    def new_booking_confirmation(self, **kw):
        current_step = 'confirmation'

        # Retour en arrière si les informations nécessaires ne sont pas présentes dans la session
        redirection = self.get_redirection(current_step)
        if redirection:
            return redirection

        values = kw
        error = dict()
        validated = False

        if 'submitted' in values:
            values.pop('submitted')
            # Champs obligatoires
            if not values.get('terms'):
                error['terms'] = True
            if not values.get('opt_in'):
                error['opt_in'] = True

            if not error:
                validated = True

        values['error_dict'] = error

        # Demande de RDV confirmée
        if validated:
            # Mise à jour du paramètree opt_out du partenaire
            if request.env.user.partner_id.opt_out:
                request.env.user.partner_id.sudo().opt_out = False
            # Création du RDV
            intervention = self._create_intervention()
            if intervention:
                # Enregistrer l'adresse de l'équipement si nécessaire
                parc_installe_id = request.session.get('booking_parc_installe_id')
                parc_installe = request.env['of.parc.installe'].browse(parc_installe_id)
                site_adresse_id = request.session.get('rdv_site_adresse_id')
                if not parc_installe.site_adresse_id or parc_installe.site_adresse_id.id != site_adresse_id:
                    parc_installe.sudo().write({'site_adresse_id': site_adresse_id})
                    request.env.cr.commit()

                # Envoyer l'email de confirmation
                mail_template = request.env['ir.model.data'].sudo().get_object(
                    'of_website_planning_booking', 'of_website_planning_booking_confirmation_mail_template')
                mail_id = mail_template.send_mail(intervention.id)
                mail = request.env['mail.mail'].sudo().browse(mail_id)
                mail.send()

                # Vider les variables de session
                request.session['rdv_creneau_id'] = False
                request.session['rdv_search_wiz_id'] = False
                request.session['rdv_date_recherche_debut'] = False
                request.session['rdv_tache_id'] = False
                request.session['rdv_site_address_id'] = False
                request.session['booking_parc_installe_id'] = False
                return request.redirect('/new_booking/thank_you')
            else:
                return request.redirect('/new_booking/slot')

        # Arrivée sur la page
        values['step_number'] = STEP_NAME_NUMBER.get(current_step, 'new')
        values['company'] = request.website.company_id
        values['parc_installe'] = request.env['of.parc.installe'].browse(
            request.session.get('booking_parc_installe_id'))
        values['adresse'] = request.env['res.partner'].browse(request.session.get('rdv_site_adresse_id'))
        task = request.env['of.planning.tache'].browse(request.session.get('rdv_tache_id'))
        values['tache'] = task
        values['creneau'] = request.env['of.tournee.rdv.line.website'].browse(request.session.get('rdv_creneau_id')).\
            exists()
        # Calcul du prix de la prestation
        pricelist = request.env.user.partner_id.property_product_pricelist or request.env.ref('product.list0', False)
        price_unit = task.product_id.sudo().with_context(pricelist=pricelist.id).price
        taxes = task.product_id.sudo().taxes_id
        if request.env.user.partner_id.company_id:
            taxes = taxes.filtered(lambda r: r.company_id == request.env.user.partner_id.company_id)
        taxes = task.fiscal_position_id.sudo().map_tax(taxes, task.product_id, request.env.user.partner_id) or []
        amounts = taxes.compute_all(
            price_unit, pricelist.currency_id, 1.0, product=task.product_id, partner=request.env.user.partner_id)
        values['price'] = amounts['total_included']
        values['company'] = request.website.company_id.sudo()
        values['terms'] = values.get('terms', False)
        values['opt_in'] = values.get('opt_in', False)

        return request.render('of_website_planning_booking.new_booking_confirmation', values)

    @http.route(['/new_booking/thank_you'], type='http', auth='user', website=True)
    def new_booking_thank_you(self, **kw):
        return request.render('of_website_planning_booking.new_booking_thank_you')

    def _create_parc_installe(self):
        vals = {}

        for key in request.params.keys():
            if key in ('modele', 'name', 'type_conduit', 'date_installation', 'annee_batiment'):
                if key != 'name' or request.params[key]:
                    vals[key] = request.params[key]
            # Les params sont renvoyés en unicode
            elif key == 'product_category_id' and request.params[key]:
                vals[key] = int(request.params[key])
            elif key == 'brand_id' and request.params[key] != 'Autre marque':
                vals[key] = int(request.params[key])
            elif key == 'extra_brand':
                vals['website_extra_brand'] = request.params[key]
            elif key == 'installateur_name':
                vals['website_installer_name'] = request.params[key]
            elif key == 'installateur_email':
                vals['website_installer_email'] = request.params[key]

        # Marque extérieur
        if request.params['brand_id'] == 'Autre marque':
            vals['brand_id'] = request.env['ir.values'].sudo().get_default(
                'of.intervention.settings', 'website_booking_default_product_brand_id')
            vals['note'] = u"Marque : %s" % request.params['extra_brand']

        vals['product_id'] = request.env.ref(
            'of_website_planning_booking.of_website_planning_booking_product_default').id
        vals['client_id'] = request.env.user.partner_id.id
        vals['website_create'] = True

        # Installateur
        if request.params.get('installateur_name') and not request.params.get('installateur_email'):
            note = u"Installé par %s" % request.params['installateur_name']
            if vals.get('note'):
                vals['note'] += "\n" + note
            else:
                vals['note'] = note
        elif request.params.get('installateur_name') and request.params.get('installateur_email'):
            partner_obj = request.env['res.partner'].sudo()
            installer = partner_obj.search([('email', '=', request.params['installateur_email'])], limit=1)
            if not installer:
                installer = partner_obj.create({
                    'name': request.params['installateur_name'],
                    'email': request.params['installateur_email'],
                    'of_installateur': True,
                })
            vals['installateur_id'] = installer.id

        new_park = request.env['of.parc.installe'].sudo().create(vals)

        # Pièces Jointes
        if 'park_attachment' in request.params:
            attached_files = request.httprequest.files.getlist('park_attachment')
            for attachment in attached_files:
                attached_file = attachment.read()
                request.env['ir.attachment'].sudo().create({
                    'name': attachment.filename,
                    'res_model': 'of.parc.installe',
                    'res_id': new_park.id,
                    'type': 'binary',
                    'datas_fname': attachment.filename,
                    'datas': attached_file.encode('base64'),
                })

        return new_park

    def _update_parc_installe(self, parc_installe_id):
        parc_installe_obj = request.env['of.parc.installe'].sudo()
        parc_installe = parc_installe_obj.browse(parc_installe_id)
        params = request.params
        updated = False
        update_vals = {}

        parc_product_category = parc_installe.product_category_id
        param_product_categ_id = params.get('product_category_id') and int(params['product_category_id'])
        if param_product_categ_id and (not parc_product_category or parc_product_category.id != param_product_categ_id):
            update_vals['product_category_id'] = param_product_categ_id
        parc_brand = parc_installe.brand_id
        param_brand_id = params.get('brand_id') and params['brand_id'] != 'Autre marque' and int(params['brand_id'])
        if params.get('brand_id') == 'Autre marque':
            param_brand_id = request.env['ir.values'].sudo().get_default(
                'of.intervention.settings', 'website_booking_default_product_brand_id')
        if param_brand_id and (not parc_brand or parc_brand.id != param_brand_id):
            update_vals['brand_id'] = param_brand_id
        if params.get('extra_brand') and params['extra_brand'] != parc_installe.website_extra_brand:
            update_vals['website_extra_brand'] = params['extra_brand']
            if not parc_installe.note or params['extra_brand'] not in parc_installe.note:
                update_vals['note'] = u"Marque : %s" % params['extra_brand']
        if params.get('modele') and params['modele'] != parc_installe.modele:
            update_vals['modele'] = params['modele']
        if params.get('name') != parc_installe.name:
            update_vals['name'] = params.get('name')
        if params.get('type_conduit') != parc_installe.type_conduit:
            update_vals['type_conduit'] = params.get('type_conduit')
        if params.get('date_installation') != parc_installe.date_installation:
            update_vals['date_installation'] = params.get('date_installation')
        if params.get('annee_batiment') != parc_installe.annee_batiment:
            update_vals['annee_batiment'] = params.get('annee_batiment')

        # Installateur
        if params.get('installateur_name') and not params.get('installateur_email'):
            if not parc_installe.note or params['installateur_name'] not in parc_installe.note:
                note = u"Installé par %s" % request.params['installateur_name']
                if update_vals.get('note'):
                    update_vals['note'] += "\n" + note
                else:
                    update_vals['note'] = note
        elif params.get('installateur_name') and params.get('installateur_email'):
            partner_obj = request.env['res.partner'].sudo()
            installer = partner_obj.search([('email', '=', params['installateur_email'])], limit=1)
            if not installer:
                installer = partner_obj.create({
                    'name': params['installateur_name'],
                    'email': params['installateur_email'],
                    'of_installateur': True,
                })
            if installer != parc_installe.installateur_id:
                update_vals['installateur_id'] = installer.id
        if params.get('installateur_name') and params['installateur_name'] != parc_installe.website_installer_name:
            update_vals['website_installer_name'] = params['installateur_name']
        if params.get('installateur_email') and params['installateur_email'] != parc_installe.website_installer_email:
            update_vals['website_installer_email'] = params['installateur_email']

        # Pièces Jointes
        if 'park_attachment' in params:
            attached_files = request.httprequest.files.getlist('park_attachment')
            for attachment in attached_files:
                attached_file = attachment.read()
                request.env['ir.attachment'].sudo().create({
                    'name': attachment.filename,
                    'res_model': 'of.parc.installe',
                    'res_id': parc_installe.id,
                    'type': 'binary',
                    'datas_fname': attachment.filename,
                    'datas': attached_file.encode('base64'),
                })
            updated = True

        if update_vals:
            if 'note' in update_vals and parc_installe.note:
                update_vals['note'] = parc_installe.note + '\n\n' + update_vals['note']
            parc_installe.write(update_vals)
            updated = True
        return updated

    def _update_address_if_necessary(self, address_id):
        partner_obj = request.env['res.partner'].sudo()
        address = partner_obj.browse(address_id)
        params = request.params
        updated = False
        update_vals = {}
        if params.get('name') and params['name'] != address.name:
            update_vals['name'] = params['name']
        if params.get('phone') and params['phone'] != address.phone:
            update_vals['phone'] = params['phone']
        if params.get('email') != address.email:
            update_vals['email'] = params['email']
        if params.get('street') and params['street'] != address.street:
            update_vals['street'] = params['street']
        if params['street2'] != address.street2:
            update_vals['street2'] = params['street2']
        if params.get('zip') and params['zip'] != address.zip:
            update_vals['zip'] = params['zip']
            # On recalcule le secteur
            if address.of_secteur_tech_id:
                secteur = request.env['of.secteur'].sudo().get_secteur_from_cp(update_vals['zip']).filtered(
                    lambda sec: sec.type in ('tech', 'tech_com'))
                if secteur:
                    update_vals['of_secteur_tech_id'] = secteur.id
                else:
                    update_vals['of_secteur_tech_id'] = False
        if params.get('city') and params['city'] != address.city:
            update_vals['city'] = params['city']
        address_country = address.country_id
        request_country_id = params.get('country_id') and int(params['country_id'])
        if request_country_id and (not address_country or address_country.id != request_country_id):
            update_vals['country_id'] = request_country_id
        if update_vals:
            address.write(update_vals)
            address.geo_code()
            updated = True
        return updated

    def _create_new_address(self, parent_id):
        partner_obj = request.env['res.partner'].sudo()
        params = request.params
        vals = {
            'parent_id': parent_id,
            'type': 'delivery',
            'name': params.get('name'),
            'email': params.get('email'),
            'phone': params.get('phone'),
            'street': params.get('street'),
            'street2': params.get('street2'),
            'zip': params.get('zip'),
            'city': params.get('city'),
            'country_id': params.get('country_id') and int(params['country_id']),
        }
        partner = partner_obj.create(vals)
        partner.geo_code()
        return partner.id

    def _update_geo_info(self):
        partner_obj = request.env['res.partner'].sudo()
        address = partner_obj.browse(request.session.get('rdv_site_adresse_id'))
        params = request.params
        updated = False
        update_vals = {}
        if params.get('geo_lat') and params['geo_lat'] != address.geo_lat:
            update_vals['geo_lat'] = params['geo_lat']
        if params.get('geo_lng') and params['geo_lng'] != address.geo_lng:
            update_vals['geo_lng'] = params['geo_lng']
        if params.get('comment') != address.of_geo_comment:
            update_vals['of_geo_comment'] = params['comment']
        if update_vals:
            address.write(update_vals)
            updated = True
        return updated

    def _get_intervention_vals(self, creneau, creneau_employee):
        tz = pytz.timezone(request.env.user.tz or 'Europe/Paris')

        compare_precision = 5
        parc_obj = request.env['of.parc.installe'].sudo()
        partner_obj = request.env['res.partner'].sudo()
        tache_obj = request.env['of.planning.tache'].sudo()
        parc_installe = parc_obj.browse(request.session.get('booking_parc_installe_id'))
        adresse = partner_obj.browse(request.session.get('rdv_site_adresse_id'))
        tache = tache_obj.browse(request.session.get('rdv_tache_id'))
        description = u""
        if adresse.of_geo_comment:
            description = u"Commentaire localisation du client : %s" % adresse.of_geo_comment
        if request.params.get('comment'):
            if description:
                description += u"<br/>"
            description += u"Commentaires additionnels du client : %s" % request.params.get('comment')

        vals = {
            'name': u"Intervention",
            'parc_installe_id': parc_installe.id,
            'address_id': adresse.id,
            'tache_id': tache.id,
            'flexible': tache.flexible,
            'employee_ids': [(4, creneau_employee.employee_id.id, 0)],
            'duree': tache.duree,
            'company_id': request.website.company_id.id,
            'state': 'draft',
            'fiscal_position_id': tache.fiscal_position_id.id or False,
            'verif_dispo': True,
            'line_ids': tache.product_id and [(0, 0, {'product_id': tache.product_id.id,
                                                      'qty': 1,
                                                      'price_unit': tache.product_id.lst_price,
                                                      'name': tache.product_id.name,
                                                      })] or False,
            'origin_interface': u"Portail web",
            'website_create': True,
            'description': description,
        }
        # Le créneau de l'employé peut commencer avant le début d'aprem,
        # on fait donc un max pour s'assurer que le RDV soit pris l'aprem
        if creneau.name.lower() == 'après-midi':
            debut_aprem_flo = 14.0  # -> à récupérer depuis de la config en backend?
            if float_compare(debut_aprem_flo, creneau_employee.date_flo, compare_precision) <= 0:
                debut_dt = creneau_employee.debut_dt
            # création d'un dt à partir de l'heure de début d'aprem
            # attention /!\ l'employé doit travailler à partir de l'heure de début d'aprem
            # @todo: gérer le cas ou l'employé commence à travailler après l'heure de début d'aprem
            else:
                time_str = hours_to_strs('time', debut_aprem_flo)
                debut_local_dt = tz.localize(datetime.strptime(creneau.date + " %s:00" % time_str, "%Y-%m-%d %H:%M:%S"))
                debut_dt = debut_local_dt.astimezone(pytz.utc).strftime("%Y-%m-%d %H:%M:%S")
        else:
            debut_dt = creneau_employee.debut_dt
        vals['date'] = debut_dt
        return vals

    def _create_intervention(self):
        interv_obj = request.env['of.planning.intervention'].sudo()
        creneau_obj = request.env['of.tournee.rdv.line.website']
        creneau = creneau_obj.browse(request.session.get('rdv_creneau_id')).exists()

        created = False
        intervention = False
        # fonctionnement basique pour la création : si le créneau backend sélectionné a été rempli entre temps
        # et que le créneau frontend est connecté à d'autre créneaux backend, essayer un autre créneau backend
        while not created and creneau.planning_ids:
            creneau_employee = creneau.planning_ids.sorted(lambda p: (p.dist_prec, p.dist_ortho_prec))[0]
            creneau_employee.button_select(sudo=True)
            vals = self._get_intervention_vals(creneau, creneau_employee)
            try:
                intervention = interv_obj.create(vals)
                intervention = intervention.with_context(from_portal=True)
                if intervention.line_ids:
                    intervention.line_ids.compute_taxes()
                # mettre à jour le nom du RDV
                intervention._onchange_address_id()
                created = True
            except ValidationError, e:
                creneau_employee.unlink()
                _logger.warning(u"Erreur à la création de RDV depuis le portail: %s", e.message)
            except Exception, e:
                creneau_employee.unlink()
                _logger.warning(u"Erreur à la création de RDV depuis le portail: %s", e.message)
        # si le créneau front n'est plus connecté à un créneau backend, le supprimer
        if not creneau.planning_ids:
            creneau.unlink()
        return intervention
