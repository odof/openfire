# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import json
import pytz
from datetime import datetime, timedelta

from odoo import http
from odoo.http import request
from odoo.tools.float_utils import float_compare
from odoo.addons.of_utils.models.of_utils import hours_to_strs


class OFWebsitePlanningBooking(http.Controller):

    @http.route(['/booking'], type='http', auth='public', website=True)
    def booking(self, **kw):
        values = kw

        values['service_list'] = request.env['of.planning.intervention.template'].search([]).mapped(
            lambda t: {'id': t.id, 'name': t.website_name or t.name})

        return request.render('of_website_planning_booking_v2.booking', values)

    @http.route(['/booking/get_partner'], type='json', auth='public', website=True)
    def get_partner(self, partner_id, **kw):
        partner = request.env['res.partner'].sudo().browse(int(partner_id))
        return json.dumps({
            'name': partner.name,
            'email': partner.email,
            'phone': partner.phone,
            'street': partner.street,
            'street2': partner.street2,
            'zip': partner.zip,
            'city': partner.city,
        })

    @http.route(['/booking/create_update_partner'], type='json', auth='public', website=True)
    def create_partner(self, partner_id, **kw):
        if not partner_id:
            return self._create_partner()
        else:
            return self._update_partner(int(partner_id))

    @http.route(['/booking/search_slots'], type='json', auth='public', website=True)
    def search_slots(self, service_id, partner_id, from_date, search_more=False, **kw):
        result = self._search_slots(int(service_id), int(partner_id), from_date, search_more=search_more)
        return [[{'name': slot.name, 'description': slot.description, 'id': slot.id} for slot in result[0]], result[1]]

    @http.route(['/booking/confirm'], type='http', auth='public', website=True, methods=['POST'])
    def confirm(self, **kw):
        values = kw

        if 'service_id' not in values or 'partner_id' not in values or 'slot_id' not in values:
            return request.redirect('/booking')

        if 'submitted' in values:
            # Demande de RDV confirmée
            template = request.env['of.planning.intervention.template'].sudo().browse(int(values['service_id']))
            partner = request.env['res.partner'].sudo().browse(int(values['partner_id']))
            slot = request.env['of.tournee.rdv.line.website'].browse(int(values['slot_id']))
            # Mise à jour du paramètre opt_out du partenaire
            if partner.opt_out:
                partner.sudo().opt_out = False
            # Création du RDV
            intervention = self._create_intervention(template, partner, slot)
            if intervention:
                # Envoyer l'email de confirmation
                mail_template = request.env['ir.model.data'].sudo().get_object(
                    'of_website_planning_booking_v2', 'booking_confirmation_mail_template')
                mail_id = mail_template.send_mail(intervention.id)
                mail = request.env['mail.mail'].sudo().browse(mail_id)
                mail.send()

                return request.render('of_website_planning_booking_v2.booking_thank_you')
            else:
                return request.redirect('/booking')

        # Arrivée sur la page
        template = request.env['of.planning.intervention.template'].sudo().browse(int(values['service_id']))
        partner = request.env['res.partner'].sudo().browse(int(values['partner_id']))
        slot = request.env['of.tournee.rdv.line.website'].browse(int(values['slot_id']))
        task = template.tache_id
        # Calcul du prix de la prestation
        pricelist = partner.property_product_pricelist or request.env.ref('product.list0', False)
        price_unit = task.product_id.with_context(pricelist=pricelist.id).price
        taxes = task.product_id.taxes_id
        if partner.company_id:
            taxes = taxes.filtered(lambda r: r.company_id == partner.company_id)
        taxes = task.fiscal_position_id.map_tax(taxes, task.product_id, partner) or request.env['account.tax']
        amounts = taxes.compute_all(price_unit, pricelist.currency_id, 1.0, product=task.product_id, partner=partner)

        values['company'] = request.website.company_id
        values['partner'] = partner
        values['task'] = task
        values['price'] = amounts['total_included']
        values['slot'] = slot

        return request.render('of_website_planning_booking_v2.booking_confirmation', values)

    def _create_partner(self):
        partner_obj = request.env['res.partner'].sudo()
        params = request.params
        vals = {
            'name': params.get('name'),
            'email': params.get('email'),
            'phone': params.get('phone'),
            'street': params.get('street'),
            'street2': params.get('street2'),
            'zip': params.get('zip'),
            'city': params.get('city'),
        }
        partner = partner_obj.create(vals)
        partner.geo_code()
        return partner.id

    def _update_partner(self, partner_id):
        partner_obj = request.env['res.partner'].sudo()
        partner = partner_obj.browse(partner_id)
        params = request.params
        update_vals = {}
        if params['name'] != partner.name:
            update_vals['name'] = params['name']
        if params['email'] != partner.email:
            update_vals['email'] = params['email']
        if params['phone'] != partner.phone:
            update_vals['phone'] = params['phone']
        if params['street'] != partner.street:
            update_vals['street'] = params['street']
        if params['street2'] != partner.street2:
            update_vals['street2'] = params['street2']
        if params['zip'] != partner.zip:
            update_vals['zip'] = params['zip']
        if params['city'] != partner.city:
            update_vals['city'] = params['city']
        if update_vals:
            partner.write(update_vals)
            partner.geo_code()
        return partner.id

    def _search_slots(self, template_id, partner_id, from_date, search_more=False):
        # Wizard de recherche
        search_type = request.env['ir.values'].sudo().get_default(
            'of.intervention.settings', 'booking_search_type')
        max_search_criteria = request.env['ir.values'].sudo().get_default(
            'of.intervention.settings', 'booking_search_max_criteria')
        if search_more and request.session.get('of_booking_wizard_id'):
            # Clic sur le bouton "Chercher plus"
            # Récupération du wizard existant
            wizard_id = request.session.get('of_booking_wizard_id')
            wizard = request.env['of.tournee.rdv'].browse(wizard_id).exists()
            # Le cron de purge des transients a supprimé l'enregistrement
            if not wizard:
                request.session['of_booking_wizard_id'] = False
                return self._search_slots(template_id, partner_id, from_date, search_more=search_more)
            compute = 'more'
            request.session['search_slot_result_nb'] += 9
        else:
            employee_ids = request.env['ir.values'].sudo().get_default(
                'of.intervention.settings', 'booking_employee_ids') or []
            day_ids = request.env['ir.values'].sudo().get_default(
                'of.intervention.settings', 'booking_opened_day_ids') or []
            search_mode = request.env['ir.values'].sudo().get_default(
                'of.intervention.settings', 'booking_search_mode')
            template = request.env['of.planning.intervention.template'].browse(template_id)
            task = template.sudo().tache_id
            wizard_vals = {
                'company_id': request.website.company_id.id,
                'partner_id': partner_id,
                'partner_address_id': partner_id,
                'tache_id': task.id,
                'date_recherche_debut': from_date,
                'duree': task.duree,
                'pre_employee_ids': [(6, 0, employee_ids)],
                'day_ids': [(6, 0, day_ids)],
                'search_mode': search_mode,
                'search_type': search_type,
            }
            wizard = request.env['of.tournee.rdv'].with_context(from_portal=True).create(wizard_vals)
            wizard._onchange_date_recherche_debut()
            request.session['of_booking_wizard_id'] = wizard.id
            compute = 'new'
            request.session['search_slot_result_nb'] = 9

        web_slots = []

        # Nombre de jours max ouverts à la réservation
        max_days = 180
        max_search_date = (datetime.today() + timedelta(days=max_days)).strftime('%Y-%m-%d')

        if compute == 'new':
            search_end_date = datetime.strptime(from_date, '%Y-%m-%d') + timedelta(days=14)
            wizard.date_recherche_fin = search_end_date.strftime('%Y-%m-%d')
            wizard.compute(sudo=True, mode=compute)

        valid_lines = wizard.planning_ids.filtered(lambda p: p.disponible)
        if search_type == 'duration':
            valid_lines = valid_lines.filtered(lambda line: line.duree_utile <= max_search_criteria)
        else:
            valid_lines = valid_lines.filtered(lambda line: line.distance_utile <= max_search_criteria)

        # Tenter jusqu'à avoir au moins 9 résultats ou ne plus être dans les jours ouverts à la réservation
        while len(valid_lines) < request.session['search_slot_result_nb'] and \
                wizard.date_recherche_fin < max_search_date:
            new_search_start_date = datetime.strptime(wizard.date_recherche_fin, "%Y-%m-%d") + timedelta(days=1)
            new_search_end_date = new_search_start_date + timedelta(days=6)
            wizard.date_recherche_debut = new_search_start_date.strftime('%Y-%m-%d')
            wizard.date_recherche_fin = min(new_search_end_date.strftime('%Y-%m-%d'), max_search_date)
            wizard.compute(sudo=True, mode='more')
            valid_lines = wizard.planning_ids.filtered(lambda p: p.disponible)
            if search_type == 'duration':
                valid_lines = valid_lines.filtered(lambda line: line.duree_utile <= max_search_criteria)
            else:
                valid_lines = valid_lines.filtered(lambda line: line.distance_utile <= max_search_criteria)

        if valid_lines:
            web_slots = wizard.build_website_creneaux(valid_lines, mode='half_day')
            web_slots = web_slots[0:request.session['search_slot_result_nb']]
        else:
            web_slots = []

        no_more_search = (wizard.date_recherche_fin >= max_search_date)

        if request.session['search_slot_result_nb'] >= 27:
            no_more_search = True

        return [web_slots, not no_more_search]

    def _create_intervention(self, template, partner, slot):
        created = False
        intervention = False
        # fonctionnement basique pour la création : si le créneau backend sélectionné a été rempli entre temps
        # et que le créneau frontend est connecté à d'autre créneaux backend, essayer un autre créneau backend
        while not created and slot.planning_ids:
            backend_slot = slot.planning_ids.sorted(lambda p: (p.dist_prec, p.dist_ortho_prec))[0]
            backend_slot.button_select(sudo=True)

            vals = self._get_intervention_vals(slot, backend_slot, template, partner)
            # try:
            intervention = request.env['of.planning.intervention'].sudo().create(vals)
            # intervention = intervention.with_context(from_portal=True)
            intervention.onchange_company_id()
            intervention.with_context(of_import_service_lines=True)._onchange_tache_id()
            intervention.with_context(of_import_service_lines=True).onchange_template_id()
            if intervention.line_ids:
                intervention.line_ids.compute_taxes()
            # mettre à jour le nom du RDV
            intervention._onchange_address_id()
            created = True
            # except ValidationError, e:
            #     creneau_employee.unlink()
            #     _logger.warning(u"Erreur à la création de RDV depuis le portail: %s", e.message)
            # except Exception, e:
            #     creneau_employee.unlink()
            #     _logger.warning(u"Erreur à la création de RDV depuis le portail: %s", e.message)
        # si le créneau front n'est plus connecté à un créneau backend, le supprimer
        if not slot.planning_ids:
            slot.unlink()
        return intervention

    def _get_intervention_vals(self, slot, backend_slot, template, partner):
        tz = pytz.timezone('Europe/Paris')

        description = ""
        if request.params.get('comment'):
            description = u"Commentaires additionnels du client : %s" % request.params.get('comment')

        vals = {
            'name': u"Intervention web",
            'partner_id': partner.id,
            'address_id': partner.id,
            'template_id': template.id,
            'tache_id': template.tache_id.id,
            'flexible': template.tache_id.flexible,
            'employee_ids': [(4, backend_slot.employee_id.id, 0)],
            'duree': template.tache_id.duree,
            'company_id': request.website.company_id.id,
            'state': 'draft',
            'fiscal_position_id': template.tache_id.fiscal_position_id.id or False,
            'verif_dispo': True,
            'line_ids': template.tache_id.product_id and [(0, 0, {
                'product_id': template.tache_id.product_id.id,
                'qty': 1,
                'price_unit': template.tache_id.product_id.lst_price,
                'name': template.tache_id.product_id.name,
            })] or False,
            'origin_interface': u"Portail web",
            'website_create': True,
            'description': description,
        }

        # Le créneau de l'employé peut commencer avant le début d'aprem,
        # on fait donc un max pour s'assurer que le RDV soit pris l'aprem
        if slot.name.lower() == 'après-midi':
            afternoon_start_hour = 14.0  # -> à récupérer depuis de la config en backend?
            if float_compare(afternoon_start_hour, backend_slot.date_flo, 5) <= 0:
                date_start = backend_slot.debut_dt
            # création d'un dt à partir de l'heure de début d'aprem
            # attention /!\ l'employé doit travailler à partir de l'heure de début d'aprem
            # @todo: gérer le cas ou l'employé commence à travailler après l'heure de début d'aprem
            else:
                time_str = hours_to_strs('time', afternoon_start_hour)
                date_start_local = tz.localize(datetime.strptime(slot.date + " %s:00" % time_str, "%Y-%m-%d %H:%M:%S"))
                date_start = date_start_local.astimezone(pytz.utc).strftime("%Y-%m-%d %H:%M:%S")
        else:
            date_start = backend_slot.debut_dt
        vals['date'] = date_start
        return vals
