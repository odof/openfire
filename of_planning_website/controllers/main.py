# -*- coding: utf-8 -*-

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

_logger = logging.getLogger(__name__)

STEP_NAME_NUMBER = {
    'nouveau': 0,
    'appareil_select': 10,
    'appareil_create': 10,
    'adresse': 20,
    'adresse_select': 20,
    'adresse_edit': 25,
    'localisation': 30,
    'prestation': 40,
    'creneau': 50,
    'confirmation': 60,
    'ok': 70,
}


class OFPlanningWebsiteController(http.Controller):

    def get_rdv_base_vals(self, **kw):
        current_step = kw.get('current_step', 'nouveau')
        vals = {
            'last_step': request.session.get('rdv_last_step'),
            'current_step': current_step,
            'step_number': STEP_NAME_NUMBER.get(current_step, 'nouveau'),
            'error_dict': kw.get('error_dict', {}),
        }
        # On met à jour l'étape en cours au moment de demander les valeurs nécessaires à l'affichage
        request.session['rdv_current_step'] = kw.get('current_step')
        return vals

    def get_redirection(self, step):
        # l'utilisateur n'est pas connecté -> on le redirige sur la page de connexion
        if request.env.uid == request.website.user_id.id:
            return request.redirect('/web/login')
        step_number = STEP_NAME_NUMBER[step] or 0
        # À ce stade, le partenaire est nécessaire
        if step_number > 0 and not request.session.get('rdv_partner_id'):
            return request.redirect('/rdv/nouveau')
        partner = request.env['res.partner'].sudo().browse(request.session.get('rdv_partner_id'))
        # si le partenaire n'a pas de parc installé, on le redirige directement sur la page de création de parc installé
        if step == 'appareil_select' and not partner.of_parc_installe_ids:
            return request.redirect('/rdv/nouveau/appareil/creation')
        # si le partenaire n'a pas d'adresse, on le redirige directement vers la création d'adresse
        if step == 'adresse_select' and not partner.street:
            request.params['mode'] = 'new'
            return request.redirect('/rdv/nouveau/adresse/edition')
            # pour une raison inconnue, `return request.redirect('/rdv/nouveau/adresse/edition')` ne fonctionne pas ici
        # À ce stade, le parc installé est nécessaire
        if step_number >= 20 and not request.session.get('rdv_parc_installe_id'):
            return request.redirect('/rdv/nouveau/appareil/selection')
        # À ce stade, l'adresse est nécessaire
        if step_number >= 30 and not request.session.get('rdv_site_adresse_id'):
            return request.redirect('/rdv/nouveau/adresse/selection')
        # À ce stade, l'adresse est nécessaire
        if step_number >= 50 and \
                not (request.session.get('rdv_tache_id') and request.session.get('rdv_date_recherche_debut')):
            return request.redirect('/rdv/nouveau/prestation')
        # À ce stade, un créneau web doit avoir été sélectionné
        if step_number >= 60:
            if not request.session.get('rdv_creneau_id'):
                return request.redirect('/rdv/nouveau/creneau')
            creneau_obj = request.env['of.tournee.rdv.line.website'].sudo()
            # Le cron d'épuration des transients a supprimé l'enregistrement -> retour à la sélection de prestation
            if not creneau_obj.browse(request.session['rdv_creneau_id']).exists():
                request.session['rdv_search_wiz_id'] = False
                return request.redirect('/rdv/nouveau/prestation')
        return ''

    @http.route(['/rdv/nouveau'], type='http', auth='user', website=True)
    def portal_rdv_nouveau(self, **kw):
        redirection = self.get_redirection('nouveau')
        if redirection:
            return redirection
        # valeurs de session nécessaires au passage à l'étape suivante
        request.session['rdv_partner_id'] = request.env.user.partner_id.id
        request.session['rdv_last_step'] = 'nouveau'

        return request.redirect('/rdv/nouveau/appareil/selection')

    @http.route(['/rdv/nouveau/appareil/selection'], type='http', auth='user', website=True)
    def portal_rdv_nouveau_appareil_select(self, **kw):
        current_step = 'appareil_select'
        # retour en arrière si les information nécessaires ne sont pas présentes dans la session
        redirection = self.get_redirection(current_step)
        if redirection:
            return redirection
        # le formulaire de l'étape sélection d'appareil a été rempli -> traitement
        if kw.get('submitted'):
            # passage à l'étape sélection d'adresse
            if kw.get('parc_installe_id'):
                request.session['rdv_parc_installe_id'] = int(kw['parc_installe_id'])
                request.session['rdv_last_step'] = 'appareil_select'
                # supprimer la valeur d'adresse stockée en session (en cas de retour et changement de parc installé
                request.session['site_adresse_id'] = False
                return request.redirect('/rdv/nouveau/adresse/selection')
            # Champ non rempli
            else:
                kw['error_dict'] = {'parc_installe_id': u"Champ non rempli"}

        # arrivée sur la page ou erreur intermédiaire
        kw['current_step'] = current_step
        vals = self.get_rdv_base_vals(**kw)
        vals['parc_installe_list'] = request.env.user.partner_id.of_parc_installe_ids
        if vals.get('parc_installe_list'):
            # Si la session a déjà un parc installé. Exemple clic sur 'retour' à l'étape adresse
            parc_installe_id = request.session.get('rdv_parc_installe_id')
            if parc_installe_id:
                parc_installe = request.env['of.parc.installe'].sudo().browse(parc_installe_id)
                vals['parc_installe'] = parc_installe.exists() or vals['parc_installe_list'][0]
            else:
                vals['parc_installe'] = vals['parc_installe_list'][0]

        return request.render('of_planning_website.rdv_nouveau_appareil_select', vals)

    @http.route(['/rdv/nouveau/appareil/creation'], type='http', auth='user', website=True)
    def portal_rdv_nouveau_appareil_create(self, **kw):
        current_step = 'appareil_create'
        # retour en arrière si les information nécessaires ne sont pas présentes dans la session
        redirection = self.get_redirection(current_step)
        if redirection:
            return redirection
        # le formulaire de l'étape sélection d'appareil a été rempli -> traitement
        if kw.get('submitted'):
            error_dict = self.get_error_dict_appareil()
            if error_dict:
                kw.pop('submitted')
                kw['error_dict'] = error_dict
                kw['last_step'] = 'appareil_create'
                return self.portal_rdv_nouveau_appareil_create(**kw)
            # passage à l'étape sélection d'adresse
            else:
                parc_installe = self._create_parc_installe()
                request.session['rdv_parc_installe_id'] = parc_installe.id
                request.session['rdv_last_step'] = 'appareil_create'
                # supprimer la valeur d'adresse stockée en session (en cas de retour et changement de parc installé
                request.session['site_adresse_id'] = False
                return request.redirect('/rdv/nouveau/adresse/selection')

        # arrivée sur la page ou erreur intermédiaire
        kw['current_step'] = current_step
        vals = self.get_rdv_base_vals(**kw)
        vals['product_categ_list'] = self._get_product_categ_list()
        vals['brand_list'] = self._get_brand_list()
        # il y a eu une erreur -> on recharge les valeurs précédentes pour les Many2one
        # pour les autres, elles sont recupérée automatiquement par t-att-value="request.params.get('nom_du_champ')"
        if vals['last_step'] == 'appareil_create':
            product_category_id = int(request.params.get('product_category_id', u"0")) or None
            brand_id = int(request.params.get('brand_id', u"0")) or None
            vals.update({
                'product_category': request.env['product.category'].sudo().browse(product_category_id),
                'brand': request.env['of.product.brand'].sudo().browse(request.params.get('brand_id')),
            })

        return request.render('of_planning_website.rdv_nouveau_appareil_create', vals)

    @http.route(['/rdv/nouveau/adresse/selection'], type='http', auth='user', website=True)
    def portal_rdv_nouveau_adresse_select(self, **kw):
        current_step = 'adresse_select'
        # retour en arrière si les information nécessaires ne sont pas présentes dans la session
        redirection = self.get_redirection(current_step)
        if redirection:
            return redirection
        # une adresse différente a été sélectionnée -> pas de nouveau rendu mais màj session
        if kw.get('site_adresse_id') and kw.get('xhr'):
            request.session['rdv_site_adresse_id'] = int(kw['site_adresse_id'])
            return 'ok'

        # arrivée sur la page ou erreur intermédiaire
        kw['current_step'] = current_step
        vals = self.get_rdv_base_vals(**kw)
        parc_installe_id = request.session.get('rdv_parc_installe_id')
        parc_installe = request.env['of.parc.installe'].sudo().browse(parc_installe_id)
        partner = parc_installe.client_id.with_context(show_address=1).sudo()
        # le parc installé n'a pas d'adresse enregistrée -> on laisse le choix
        if not parc_installe.site_adresse_id:
            adresse_list = partner.search([
                ("id", "child_of", parc_installe.client_id.commercial_partner_id.ids),
                '|', ("type", "in", ["delivery", "other"]),
                ("id", "=", parc_installe.client_id.commercial_partner_id.id)
            ], order='id desc')
        else:
            adresse_list = parc_installe.site_adresse_id
        vals['parc_installe'] = parc_installe
        vals['adresse_list'] = adresse_list
        vals['adresse'] = parc_installe.site_adresse_id or parc_installe.client_id
        vals['site_adresse_id'] = request.session.get('rdv_site_adresse_id', vals['adresse'].id)
        request.session['rdv_site_adresse_id'] = vals['site_adresse_id']
        return request.render('of_planning_website.rdv_nouveau_adresse_select', vals)

    @http.route(['/rdv/nouveau/adresse/edition'], type='http', auth='user', website=True)
    def portal_rdv_nouveau_adresse_edit(self, **kw):
        current_step = 'adresse_edit'
        # retour en arrière si les information nécessaires ne sont pas présentes dans la session
        redirection = self.get_redirection(current_step)
        if redirection:
            return redirection
        # le formulaire a été remplis -> traitement
        if kw.get('submitted'):
            error_dict = self.get_error_dict_address()
            if error_dict:
                kw.pop('submitted')
                kw['error_dict'] = error_dict
                kw['last_step'] = 'adresse_edit'
                return self.portal_rdv_nouveau_adresse_edit(**kw)
            if kw.get('mode') == 'first':
                site_adresse_id = request.session.get('rdv_partner_id')
            elif kw.get('mode') == 'edit':
                site_adresse_id = request.session.get('rdv_site_adresse_id')
            else:
                site_adresse_id = False
            if site_adresse_id:
                self._update_address_if_necessary(site_adresse_id)
            else:
                site_address_id = self._create_new_address(request.session.get('rdv_partner_id'))
                request.session['rdv_site_adresse_id'] = site_address_id
            return request.redirect('/rdv/nouveau/adresse/selection')

        kw['current_step'] = current_step
        vals = self.get_rdv_base_vals(**kw)
        vals['last_step'] = 'adresse_edit'
        parc_installe_id = request.session.get('rdv_parc_installe_id')
        parc_installe = request.env['of.parc.installe'].sudo().browse(parc_installe_id)
        vals['parc_installe'] = parc_installe
        partner_obj = request.env['res.partner'].with_context(show_address=1).sudo()
        vals['country_list'] = request.env['res.country'].sudo().search([])
        # première adresse -> kw vide
        # nouvelle adresse -> 'mode': 'new' dans kw
        # modif adresse -> 'site_adresse_id' dans kw
        mode = kw.get('mode', kw.get('site_adresse_id') and 'edit' or 'first')
        vals['mode'] = mode
        if mode == 'first':
            vals['partner'] = partner_obj.browse(request.session.get('rdv_partner_id'))
            vals['country'] = vals['partner'].country_id or request.env['res.country'].sudo().search(
                [('name', '=', u"France")], limit=1)
            vals['adresse_principale'] = True
        elif mode == 'new':
            vals['parent'] = partner_obj.browse(request.session.get('rdv_partner_id'))
            vals['partner'] = partner_obj
            vals['country'] = vals['parent'].country_id or request.env['res.country'].sudo().search(
                [('name', '=', u"France")], limit=1)
            vals['adresse_principale'] = False
        else:
            vals['partner'] = partner_obj.browse(int(kw['site_adresse_id']))
            if vals['partner'].id == request.session.get('rdv_partner_id'):
                vals['adresse_principale'] = True
            vals['country'] = vals['partner'].country_id or request.env['res.country'].sudo().search(
                [('name', '=', u"France")], limit=1)

        return request.render('of_planning_website.rdv_nouveau_adresse_edit', vals)

    @http.route(['/rdv/nouveau/localisation'], type='http', auth="public", website=True)
    def portal_rdv_nouveau_localisation(self, **kw):
        current_step = 'localisation'
        # retour en arrière si les information nécessaires ne sont pas présentes dans la session
        redirection = self.get_redirection(current_step)
        if redirection:
            return redirection
        # arrivée sur la page
        if not kw.get('submitted'):
            try:
                google_maps_api_key = request.env['ir.config_parameter'].sudo().get_param('google_maps_api_key', '')
                map_lat_lng = []
                partner_obj = request.env['res.partner'].sudo()
                partner = partner_obj.browse(request.session.get('rdv_site_adresse_id'))
                map_lat_lng.append({'name': partner.name, 'geo_lat': partner.geo_lat, 'geo_lng': partner.geo_lng, })
            except Exception, e:
                _logger.error(
                    u"Erreur lors de l'affichage de la carte de l'adresse d'installations : %s" % tools.ustr(e))
                return request.render("website.403")

            kw['current_step'] = 'localisation'
            vals = self.get_rdv_base_vals(**kw)
            vals.update({
                'last_step': 'adresse_select',
                'googleAPIKey': google_maps_api_key,
                'map_lat_lng': json.dumps(map_lat_lng),
                'of_geo_comment': partner.of_geo_comment,
            })
            return request.render('of_planning_website.rdv_nouveau_localisation', vals)
        # le formulaire de l'étape localisation a été rempli -> traitement et passage à l'étape créneau
        else:
            if kw.get('comment'):
                self._update_geo_comment()
            return request.redirect('/rdv/nouveau/prestation')

    @http.route(['/rdv/nouveau/prestation'], type='http', auth="public", website=True)
    def portal_rdv_nouveau_prestation(self, **kw):
        current_step = 'prestation'
        # retour en arrière si les information nécessaires ne sont pas présentes dans la session
        redirection = self.get_redirection(current_step)
        if redirection:
            return redirection
        # le formulaire de l'étape localisation a été rempli -> traitement et passage à l'étape créneau
        if kw.get('submitted'):
            error_dict = self.get_error_dict_prestation()
            if error_dict:
                kw.pop('submitted')
                kw['error_dict'] = error_dict
                kw['last_step'] = 'prestation'
                return self.portal_rdv_nouveau_prestation(**kw)
            # les champs du formulaire sont correctement remplis
            request.session['rdv_tache_id'] = int(kw['tache_id'])
            request.session['rdv_date_recherche_debut'] = kw['date_recherche_debut']
            request.session['rdv_last_step'] = 'prestation'
            # Marquer pour une nouvelle recherche. les perfs pourraient être améliorées en vérifiant
            # si l'adresse / la prestation / la date a effectivement changé depuis la denière recherche
            # (en cas de retour a une étape précédente par exemple)
            request.session['rdv_search_wiz_id'] = False
            request.session['rdv_creneau_id'] = False
            return request.redirect('/rdv/nouveau/creneau')

        # arrivée sur la page
        # valeurs
        kw['current_step'] = 'prestation'
        vals = self.get_rdv_base_vals(**kw)
        vals.update({
            'last_step': kw.get('last_step', 'localisation'),
        })
        vals['tache_list'] = self._get_tache_list()
        if vals.get('tache_list'):
            # Si la session a déjà une tâche. Exemple clic sur 'retour' à l'étape creneau
            tache_id = request.session.get('rdv_tache_id')
            if tache_id:
                tache = request.env['of.planning.tache'].sudo().browse(tache_id)
                vals['tache'] = tache.exists() or vals['tache_list'][0]
            else:
                vals['tache'] = vals['tache_list'][0]
        demain_da = fields.Date.from_string(fields.Date.today()) + timedelta(days=1)
        demain_str = fields.Date.to_string(demain_da)
        date_deb = request.session.get('rdv_date_recherche_debut', demain_str)
        vals['date_recherche_debut'] = date_deb >= demain_str and date_deb or demain_str
        return request.render('of_planning_website.rdv_nouveau_prestation', vals)

    @http.route(['/rdv/nouveau/creneau'], type='http', auth="public", website=True)
    def portal_rdv_nouveau_creneau(self, **kw):
        """
        Lancer la recherche de créneau si nécessaire
        """
        current_step = 'creneau'
        # retour en arrière si les information nécessaires ne sont pas présentes dans la session
        redirection = self.get_redirection(current_step)
        if redirection:
            return redirection
        # un créneau différent vient d'être sélectionné
        if kw.get('creneau_id') and kw.get('xhr'):
            creneau_id = int(kw['creneau_id'])
            request.session['rdv_creneau_id'] = creneau_id
            creneau = request.env['of.tournee.rdv.line.website'].browse(creneau_id).exists()
            creneau.button_select(sudo=True)
            return 'ok'

        # lancer la recherche
        mode = 'demi-journee'  # 'journee' -> appeler la config backend pour choisir le mode
        creneaux = []
        compute = ''
        # il faut générer un nouveau wizard de recherche
        if not (request.session.get('rdv_search_wiz_id') and request.session.get('rdv_creneau_id')):
            tache = request.env['of.planning.tache'].sudo().browse(request.session.get('rdv_tache_id'))
            wizard_vals = {
                'company_id': request.website.company_id.id,
                'partner_id': request.session.get('rdv_partner_id'),
                'partner_address_id': request.session.get('rdv_site_adresse_id'),
                'tache_id': request.session.get('rdv_tache_id'),
                'date_recherche_debut': request.session.get('rdv_date_recherche_debut'),
                'duree': tache.duree,
            }
            search_wizard = request.env['of.tournee.rdv'].create(wizard_vals)
            search_wizard._onchange_date_recherche_debut()
            search_wizard._onchange_mode_recherche()
            request.session['rdv_search_wiz_id'] = search_wizard.id
            request.session['rdv_creneau_id'] = False
            compute = 'new'
        else:
            # récupération du wizard existant
            search_wizard_id = request.session.get('rdv_search_wiz_id')
            search_wizard = request.env['of.tournee.rdv'].browse(search_wizard_id).exists()
            # le cron de purge des transients a supprimé l'enregistrement
            if not search_wizard:
                request.session['rdv_creneau_id'] = False
                request.session['rdv_search_wiz_id'] = False
                return request.redirect('/rdv/nouveau/creneau')
            # clic sur le bouton "Chercher plus"
            if kw.get('submitted') and kw.get('load_more'):
                date_da = fields.Date.from_string(search_wizard.date_recherche_fin)
                date_da += timedelta(days=1)
                search_wizard.date_recherche_debut = fields.Date.to_string(date_da)
                date_da += timedelta(days=6)
                search_wizard.date_recherche_fin = fields.Date.to_string(date_da)
                compute = 'more'

        if compute:
            search_wizard.compute(sudo=True, mode=compute)
            cmp_try = 0
            # tenter jusqu'à avoir un résultat ou avoir parcouru 5 semaines
            while not search_wizard.planning_ids.filtered(lambda p: p.disponible) and cmp_try < 5:
                date_da = fields.Date.from_string(search_wizard.date_recherche_fin)
                date_da += timedelta(days=1)
                search_wizard.date_recherche_debut = fields.Date.to_string(date_da)
                date_da += timedelta(days=6)
                search_wizard.date_recherche_fin = fields.Date.to_string(date_da)
                search_wizard.compute(sudo=True, mode='more')
                cmp_try += 1
            if search_wizard.planning_ids.filtered(lambda p: p.disponible):
                creneaux_web = search_wizard.build_website_creneaux(mode=mode)
                if creneaux_web:
                    creneau_selected = creneaux_web.get_closer_one()
                    request.session['rdv_creneau_id'] = creneau_selected.id
                else:
                    creneau_selected = False
            else:
                creneaux_web = []
                creneau_selected = False
        else:
            creneaux_web = search_wizard.website_creneaux_ids
            creneau_selected = request.env['of.tournee.rdv.line.website'].browse(request.session.get('rdv_creneau_id'))
        # s'assurer qu'il y a un seul créneau sélectionné
        # en cas de raifraichissement de page après bouton "chercher plus" par exemple
        if creneau_selected and creneau_selected.exists():
            creneau_selected.button_select(sudo=True)

        # grouper les créneaux par semaines pour un affichage propre
        creneaux_web_week = {}
        for creneau_web in creneaux_web:
            date_creneau_da = fields.Date.from_string(creneau_web.date)
            week_number = date_creneau_da.isocalendar()[1]
            if mode == 'journee':
                if week_number not in creneaux_web_week:
                    creneaux_web_week[week_number] = [creneau_web]
                else:
                    creneaux_web_week[week_number].append(creneau_web)
            else:
                # quand on n'est pas en mode journée, il y a un niveau de profondeur supplémentaire pour s'assurer
                # que tous les créneaux de la même journée soient dans la même colonne
                if week_number not in creneaux_web_week:
                    # on utilise un OrderedDict pour conserver l'ordre des jours
                    creneaux_web_week[week_number] = OrderedDict()
                    creneaux_web_week[week_number][creneau_web.date] = [creneau_web]
                elif creneau_web.date not in creneaux_web_week[week_number]:
                    creneaux_web_week[week_number][creneau_web.date] = [creneau_web]
                # mettre les créneaux du matin en premier
                elif creneau_web.key.endswith('matin'):
                    creneaux_web_week[week_number][creneau_web.date].insert(0, creneau_web)
                else:
                    creneaux_web_week[week_number][creneau_web.date].append(creneau_web)

        kw['current_step'] = current_step
        vals = self.get_rdv_base_vals(**kw)
        vals['mode'] = mode
        vals['creneaux_grouped'] = creneaux_web_week
        vals['creneau_selected'] = creneau_selected
        return request.render('of_planning_website.rdv_nouveau_creneau', vals)

    @http.route(['/rdv/nouveau/confirmation'], type='http', auth="public", website=True)
    def portal_rdv_nouveau_confirmation(self, **kw):
        current_step = 'confirmation'
        # retour en arrière si les information nécessaires ne sont pas présentes dans la session
        redirection = self.get_redirection(current_step)
        if redirection:
            return redirection
        parc_obj = request.env['of.parc.installe'].sudo()
        partner_obj = request.env['res.partner'].sudo()
        tache_obj = request.env['of.planning.tache'].sudo()
        creneau_obj = request.env['of.tournee.rdv.line.website']
        interv_obj = request.env['of.planning.intervention'].sudo()
        # demande de RDV confirmée par l'utilisateur portail
        if kw.get('submitted'):
            # tentative de création du RDV
            intervention = self._create_intervention()
            if intervention:
                # Enregistrer l'adresse de l'appareil si nécessaire
                parc_installe_id = request.session.get('rdv_parc_installe_id')
                parc_installe = request.env['of.parc.installe'].sudo().browse(parc_installe_id)
                site_adresse_id = request.session.get('rdv_site_adresse_id')
                if not parc_installe.site_adresse_id or parc_installe.site_adresse_id.id != site_adresse_id:
                    parc_installe.write({'site_adresse_id': site_adresse_id})
                    request.env.cr.commit()
                # vider les variables de session
                request.session['rdv_creneau_id'] = False
                request.session['rdv_search_wiz_id'] = False
                request.session['rdv_date_recherche_debut'] = False
                request.session['rdv_tache_id'] = False
                request.session['rdv_site_address_id'] = False
                request.session['rdv_parc_installe_id'] = False
                return request.redirect('/rdv/nouveau/ok')
            else:
                return request.redirect('/rdv/nouveau/creneau')

        # Arrivée sur la page
        kw['current_step'] = current_step
        vals = self.get_rdv_base_vals(**kw)
        vals['last_step'] = 'creneau'
        vals['parc_installe'] = parc_obj.browse(request.session.get('rdv_parc_installe_id'))
        vals['adresse'] = partner_obj.browse(request.session.get('rdv_site_adresse_id'))
        vals['tache'] = tache_obj.browse(request.session.get('rdv_tache_id'))
        vals['creneau'] = creneau_obj.browse(request.session.get('rdv_creneau_id')).exists()
        return request.render('of_planning_website.rdv_nouveau_confirmation', vals)

    @http.route(['/rdv/nouveau/ok'], type='http', auth="public", website=True)
    def portal_rdv_nouveau_ok(self, **kw):
        current_step = 'ok'

        # Arrivée sur la page
        kw['current_step'] = current_step
        vals = self.get_rdv_base_vals(**kw)
        vals['last_step'] = 'confirmation'
        return request.render('of_planning_website.rdv_nouveau_ok', vals)

    def get_error_dict_appareil(self):
        params = request.params
        error_dict = {}
        error_message = []
        # champs obligatoires
        if not params.get('product_category_id'):
            error_dict['product_category_id'] = True
            error_message.append(u"Le champ 'Catégorie d'article' est obligatoire")
        if not params.get('brand_id'):
            error_dict['brand_id'] = True
            error_message.append(u"Le champ 'Marque' est obligatoire")
        if not params.get('modele'):
            error_dict['modele'] = True
            error_message.append(u"Le champ 'Modèle' est obligatoire")
        if not params.get('name'):
            error_dict['name'] = True
            error_message.append(u"Le champ 'Nº de série' est obligatoire")
        # validation de champs
        # Ne pas tenter la création si le numéro de série existe déjà dans la base
        if request.env['of.parc.installe'].sudo().search([('name', '=', params.get('name')),
                                                          ('name', '!=', False)], limit=1):
            error_dict['name'] = True
            error_message.append(u"Ce numéro de série existe déjà dans notre logiciel,"
                                 u" veuillez vérifier sa valeur et contacter le service client si besoin.")
        if error_dict:
            error_dict['error_message'] = error_message

        return error_dict

    def get_error_dict_address(self):
        params = request.params
        error_dict = {}
        error_message = []
        # pour l'adresse principale : le nom, le téléphone, l'email sont obligatoires
        if params.get('adresse_principale'):
            if not params.get('name'):
                error_dict['name'] = True
                error_message.append(u"Le champ 'NOM Prénom' est obligatoire")
            if not params.get('email'):
                error_dict['email'] = True
                error_message.append(u"Le champ 'Email' est obligatoire")
            if not params.get('phone'):
                error_dict['phone'] = True
                error_message.append(u"Le champ 'Téléphone' est obligatoire")
        # pour toutes les adresses : la rue, le code postal, la ville, le pays sont obligatoires
        if not params.get('street'):
            error_dict['street'] = True
            error_message.append(u"Le champ 'Rue' est obligatoire")
        if not params.get('zip'):
            error_dict['zip'] = True
            error_message.append(u"Le champ 'Code postal' est obligatoire")
        if not params.get('city'):
            error_dict['city'] = True
            error_message.append(u"Le champ 'Ville' est obligatoire")
        if not params.get('country_id'):
            error_dict['country_id'] = True
            error_message.append(u"Le champ 'Pays' est obligatoire")
        if error_dict:
            error_dict['error_message'] = error_message

        return error_dict

    def get_error_dict_prestation(self):
        params = request.params
        error_dict = {}
        error_message = []
        # champs obligatoires
        if not params.get('tache_id'):
            error_dict['tache_id'] = True
            error_message.append(u"Le champ 'Prestation' est obligatoire")
        if not params.get('date_recherche_debut'):
            error_dict['date_recherche_debut'] = True
            error_message.append(u"Le champ 'Date de début de recherche de créneau' est obligatoire")
        # validation de champs
        # la date de début de recherche doit être après aujourd'hui
        date_recherche_debut_da = fields.Date.from_string(params.get('date_recherche_debut'))
        demain_da = fields.Date.from_string(fields.Date.today()) + timedelta(days=1)
        # autoriser la configuration du nombre de jour max coté backend ?
        max_jour = 60
        max_date_debut_da = fields.Date.from_string(fields.Date.today()) + timedelta(days=max_jour)
        if date_recherche_debut_da < demain_da:
            error_dict['date_recherche_debut'] = True
            error_message.append(u"La date de début de recherche doit être après aujourd'hui")
        if date_recherche_debut_da > max_date_debut_da:
            error_dict['date_recherche_debut'] = True
            error_message.append(u"La date de début de recherche doit être avant %d jours" % max_jour)
        if error_dict:
            error_dict['error_message'] = error_message

        return error_dict

    def _get_product_categ_list(self):
        return request.env['product.category'].sudo().search([])

    def _get_brand_list(self):
        return request.env['of.product.brand'].sudo().search([])

    def _get_tache_list(self):
        return request.env['of.planning.tache'].sudo().search([])

    def _get_installateur_id(self):
        if not (request.params.get('installateur_email') and request.params.get('installateur_name')):
            return False
        partner_obj = request.env['res.partner'].sudo()
        installateur = partner_obj.search([('email', '=', request.params['installateur_email'])], limit=1)
        if not installateur:
            vals = {
                'name': request.params['installateur_name'],
                'email': request.params['installateur_email'],
                'of_installateur': True,
            }
            installateur = partner_obj.create(vals)
        elif not installateur.of_installateur:
            installateur.of_installateur = True
        return installateur.id

    def _get_parc_vals(self):
        vals = {}
        for key in request.params.keys():
            if key in ('modele', 'name', 'type_conduit', 'date_installation'):
                vals[key] = request.params[key]
            # les params sont renvoyés en unicode
            elif key in ('product_category_id', 'brand_id', 'annee_batiment') and request.params[key]:
                vals[key] = int(request.params[key])
        vals['product_id'] = request.env.ref('of_parc_installe.of_parc_installe_product_product_default').id
        vals['installateur_id'] = self._get_installateur_id()
        vals['client_id'] = request.env.user.partner_id.id
        vals['site_adresse_id'] = request.env.user.partner_id.id
        vals['website_create'] = True
        return vals

    def _create_parc_installe(self):
        parc_obj = request.env['of.parc.installe'].sudo()
        vals = self._get_parc_vals()
        parc = parc_obj.create(vals)

        return parc

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
        if params.get('city') and params['city'] != address.city:
            update_vals['city'] = params['city']
        address_country = address.country_id
        request_country_id = params.get('country_id') and int(params['country_id'])
        if request_country_id and (not address_country or address_country.id != request_country_id):
            update_vals['country_id'] = request_country_id
        if update_vals:
            # # désactiver la géoloc auto -> Sera Géocodé par le compte google du distributeur
            # address = address.with_context(from_import=True)
            address.write(update_vals)
            request.env.cr.commit()
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
        request.env.cr.commit()
        return partner.id

    def _update_geo_comment(self):
        partner_obj = request.env['res.partner'].sudo()
        # la verif de présence de la valeur dans la session est faite en amont
        address = partner_obj.browse(request.session.get('rdv_site_adresse_id'))
        comment = request.params.get('comment')
        address.write({'of_geo_comment': comment})
        request.env.cr.commit()

    def _get_intervention_vals(self, creneau, creneau_employee):
        """
        :return: dictionnaires de valeurs pour la création du RDV Tech
        """
        tz = pytz.timezone(request.env.user.tz or 'Europe/Paris')

        compare_precision = 5
        parc_obj = request.env['of.parc.installe'].sudo()
        partner_obj = request.env['res.partner'].sudo()
        tache_obj = request.env['of.planning.tache'].sudo()
        parc_installe = parc_obj.browse(request.session.get('rdv_parc_installe_id'))
        adresse = partner_obj.browse(request.session.get('rdv_site_adresse_id'))
        tache = tache_obj.browse(request.session.get('rdv_tache_id'))
        vals = {
            'name': u"Intervention",
            'parc_installe_id': parc_installe.id,
            'address_id': adresse.id,
            'tache_id': tache.id,
            'employee_ids': [(4, creneau_employee.employee_id.id, 0)],
            'duree': tache.duree,
            'company_id': request.website.company_id.id,
            'state': 'draft',
            'verif_dispo': True,
            'origin_interface': u"Portail web",
            'website_create': True,
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
