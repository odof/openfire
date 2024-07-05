# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import logging
import json
from datetime import datetime, timedelta

import pytz

from odoo import http
from odoo.http import request
from odoo.tools.float_utils import float_compare

from odoo.addons.of_utils.models.of_utils import hours_to_strs

_logger = logging.getLogger(__name__)


class OFWebsitePlanningBooking(http.Controller):

    @http.route(['/booking'], type='http', auth='public', website=True)
    def booking(self, **kw):
        values = kw

        values['logged'] = True
        values['logged_partner_id'] = request.env.user.partner_id.id
        booking_company_id = self._get_company_id()
        if request.env.uid == request.website.user_id.id:
            values['logged'] = False
            values['logged_partner_id'] = 0
            new_customer = request.env['ir.values'].sudo().get_default(
                'of.intervention.settings', 'booking_open_new_customer') or False
            if not new_customer:
                # La prise de RDV n'est pas ouverte aux nouveaux clients et l'utilisateur n'est pas connecté
                # -> on le redirige sur la page de connexion
                return request.redirect('/web/login')

        service_list = []
        display_price = request.env['ir.values'].sudo().with_context(force_company=booking_company_id).get_default(
            'of.intervention.settings', 'booking_display_price') or False
        partner = request.env.user.partner_id
        pricelist = partner.property_product_pricelist or request.env.ref('product.list0', False)
        for template in request.env['of.planning.intervention.template'].search([]):
            vals = {'id': template.id, 'name': template.website_name or template.name}
            if display_price:
                price = self._get_service_price(template.sudo(), False, partner, pricelist)
                vals['name'] = vals['name'] + " - " + "%.2f €" % price
            service_list.append(vals)
        values['service_list'] = service_list

        contract_list = []
        address_list = []
        if values['logged']:
            contract_type = request.env.ref('of_service.of_service_type_maintenance', raise_if_not_found=False)
            contract_list = request.env['of.service'].sudo().search([
                ('type_id', '=', contract_type.id),  # si pas de contract_type alors erreur
                ('base_state', '=', 'calculated'),
                ('state', 'not in', ('draft', 'done', 'cancel')),
                ('recurrence', '=', True),
                '|',
                ('partner_id', 'child_of', request.env.user.partner_id.id),
                ('address_id', 'child_of', request.env.user.partner_id.id),
            ]).mapped(lambda s: {'id': s.id, 'name': s.template_id.website_name or s.template_id.name or s.name})
            address_list.append({
                'id': request.env.user.partner_id.id,
                'name': "%s - %s" % (request.env.user.partner_id.zip, request.env.user.partner_id.city)
            })
            address_list += request.env.user.partner_id.child_ids.filtered(lambda child: child.zip and child.city).\
                mapped(lambda c: {'id': c.id, 'name': "%s - %s" % (c.zip, c.city)})
        values['contract_list'] = contract_list
        values['address_list'] = address_list

        if values.get('intervention_id'):
            intervention = request.env['of.planning.intervention'].sudo().browse(int(values['intervention_id']))
            values['upd_service_id'] = intervention.template_id.id
            values['upd_contract_id'] = intervention.service_id.id
            values['upd_address_id'] = intervention.address_id.id

        values['morning_hours_label'] = request.env['ir.values'].sudo().with_context(
            force_company=booking_company_id).get_default(
                'of.intervention.settings', 'booking_morning_hours_label') or ""
        values['afternoon_hours_label'] = request.env['ir.values'].sudo().with_context(
            force_company=booking_company_id).get_default(
                'of.intervention.settings', 'booking_afternoon_hours_label') or ""

        return request.render('of_website_planning_booking_v2.booking', values)

    @http.route(['/booking/get_better_zip'], type='json', auth='public', website=True)
    def get_better_zip(self, zip_name, **kw):
        better_zip = request.env['res.better.zip'].search([('display_name', '=', zip_name)], limit=1)
        if better_zip:
            return json.dumps({
                'name': better_zip.name,
                'city': better_zip.city,
            })
        return False

    @http.route(['/booking/get_partner'], type='json', auth='public', website=True)
    def get_partner(self, partner_id, **kw):
        values = kw

        if 'contract_id' in values and values.get('contract_id') != 'null':
            service = request.env['of.service'].sudo().browse(int(values['contract_id']))
            partner = service.address_id or service.partner_id
        else:
            partner = request.env['res.partner'].sudo().browse(int(partner_id))

        return json.dumps({
            'id': partner.id,
            'name': partner.name or partner.parent_id.name,
            'email': partner.email or partner.parent_id.email,
            'phone': partner.mobile or partner.parent_id.mobile,
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
    def search_slots(self, service_id, contract_id, partner_id, from_date, search_more=False, **kw):
        result = self._search_slots(
            service_id and int(service_id), contract_id and int(contract_id), int(partner_id), from_date,
            search_more=search_more)
        return [[{'name': slot.name, 'description': slot.description, 'id': slot.id} for slot in result[0]], result[1]]

    @http.route(['/booking/confirm'], type='http', auth='public', website=True, methods=['POST'])
    def confirm(self, **kw):
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

        # Si il manque les valeurs service_id ET contract_id
        # ou une valeur parmi partner_id, slot_id
        if all(
            not values.get(key) or values.get(key) == 'null'
            for key in ['service_id', 'contract_id']
        ) or any(
            not values.get(key) or values.get(key) == 'null'
            for key in ['partner_id', 'slot_id']
        ):
            return request.redirect('/booking')

        if validated:
            # Demande de RDV confirmée
            template = service = False
            if values.get('service_id') and values.get('service_id') != 'null':
                template = request.env['of.planning.intervention.template'].sudo().browse(int(values['service_id']))
            elif values.get('contract_id') and values.get('contract_id') != 'null':
                service = request.env['of.service'].sudo().browse(int(values['contract_id']))
            partner = request.env['res.partner'].sudo().browse(int(values['partner_id']))
            slot = request.env['of.tournee.rdv.line.website'].browse(int(values['slot_id']))
            # Mise à jour du paramètre opt_out du partenaire
            if partner.opt_out:
                partner.sudo().opt_out = False
            intervention = False
            update = False
            if values.get('intervention_id'):
                # Mise à jour du RDV
                intervention = request.env['of.planning.intervention'].sudo().browse(int(values['intervention_id']))
                update = True
            intervention = self._create_update_intervention(intervention, template, service, partner, slot)
            if update:
                return request.redirect('/my/rdvs')
            elif intervention:
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
        booking_company_id = self._get_company_id()
        template = request.env['of.planning.intervention.template']
        service = request.env['of.service']
        service_name = ""
        if values.get('service_id') and values.get('service_id') != 'null':
            template = request.env['of.planning.intervention.template'].sudo().browse(int(values['service_id']))
            service_name = template.website_name or template.name
        elif values.get('contract_id') and values.get('contract_id') != 'null':
            service = request.env['of.service'].sudo().browse(int(values['contract_id']))
            service_name = service.template_id.website_name or service.template_id.name or service.name
        partner = request.env['res.partner'].sudo().browse(int(values['partner_id']))
        slot = request.env['of.tournee.rdv.line.website'].browse(int(values['slot_id']))
        custom_note = request.env['ir.values'].sudo().with_context(force_company=booking_company_id).get_default(
            'of.intervention.settings', 'booking_validation_note') or ""
        # Calcul du prix de la prestation
        display_price = request.env['ir.values'].sudo().with_context(force_company=booking_company_id).get_default(
            'of.intervention.settings', 'booking_display_price') or False
        price = 0
        if display_price:
            if service:
                display_price = False
            else:
                pricelist = partner.property_product_pricelist or request.env.ref('product.list0', False)
                price = self._get_service_price(template.sudo(), service.sudo(), partner, pricelist)

        values['company'] = request.env['res.company'].sudo().browse(booking_company_id)
        values['partner'] = partner
        values['service_name'] = service_name
        values['display_price'] = display_price
        values['price'] = price
        values['slot'] = slot
        values['custom_note'] = custom_note
        values['terms'] = values.get('terms', False)
        values['opt_in'] = values.get('opt_in', False)

        return request.render('of_website_planning_booking_v2.booking_confirmation', values)

    @http.route(['/booking/error'], type='http', auth='public', website=True)
    def booking_error(self, **kw):
        return request.render('of_website_planning_booking_v2.booking_error')

    def _get_company_id(self):
        # Calcul de la société à prendre en compte
        booking_company_id = request.env['ir.values'].sudo().get_default(
            'of.intervention.settings', 'booking_intervention_company_id') or request.website.company_id.id
        if request.env.uid == request.website.user_id.id:
            return booking_company_id
        else:
            booking_use_partner_company = request.env['ir.values'].sudo().get_default(
                'of.intervention.settings', 'booking_use_partner_company') or True
            if booking_use_partner_company:
                return request.env.user.partner_id.company_id.id or booking_company_id
            else:
                return booking_company_id

    def _get_service_price(self, template, service, partner, pricelist):
        total_price = 0
        if template:
            lines = template.line_ids
            fiscal_position = template.fiscal_position_id
        else:
            lines = service.line_ids
            fiscal_position = service.fiscal_position_id

        for line in lines:
            price_unit = line.product_id.with_context(pricelist=pricelist.id).price
            taxes = line.product_id.taxes_id
            if partner.company_id:
                taxes = taxes.filtered(lambda r: r.company_id == partner.company_id)
            taxes = fiscal_position.map_tax(taxes, line.product_id, partner) or request.env['account.tax']
            amounts = taxes.compute_all(
                price_unit, pricelist.currency_id, 1.0, product=line.product_id, partner=partner)
            total_price += amounts['total_included']

        return total_price

    def _create_partner(self):
        partner_obj = request.env['res.partner'].sudo()
        params = request.params
        vals = {
            'name': params.get('name'),
            'email': params.get('email'),
            'mobile': params.get('phone'),
            'street': params.get('street'),
            'street2': params.get('street2'),
            'zip': params.get('zip'),
            'city': params.get('city'),
        }
        if request.env.uid != request.website.user_id.id:
            vals['parent_id'] = request.env.user.partner_id.id
        partner = partner_obj.create(vals)
        partner.geo_code()
        return partner.id

    def _update_partner(self, partner_id):
        partner_obj = request.env['res.partner'].sudo()
        partner = partner_obj.browse(partner_id)
        params = request.params
        update_vals = {}
        if params['name'] != partner.name or (partner.parent_id and params['name'] != partner.parent_id.name):
            update_vals['name'] = params['name']
        if params['email'] != partner.email or (partner.parent_id and params['email'] != partner.parent_id.email):
            update_vals['email'] = params['email']
        if params['phone'] != partner.mobile or (partner.parent_id and params['phone'] != partner.parent_id.mobile):
            update_vals['mobile'] = params['phone']
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

    def _search_slots(self, template_id, service_id, partner_id, from_date, search_more=False):
        # Wizard de recherche
        booking_company_id = self._get_company_id()
        search_type = request.env['ir.values'].sudo().with_context(
            force_company=booking_company_id).get_default('of.intervention.settings', 'booking_search_type')
        max_search_criteria = request.env['ir.values'].sudo().with_context(
            force_company=booking_company_id).get_default('of.intervention.settings', 'booking_search_max_criteria')
        allow_empty_days = request.env['ir.values'].sudo().with_context(
            force_company=booking_company_id).get_default('of.intervention.settings', 'booking_allow_empty_days')
        if search_more and request.session.get('of_booking_wizard_id'):
            # Clic sur le bouton "Chercher plus"
            # Récupération du wizard existant
            wizard_id = request.session.get('of_booking_wizard_id')
            wizard = request.env['of.tournee.rdv'].browse(wizard_id).exists()
            # Le cron de purge des transients a supprimé l'enregistrement
            if not wizard:
                request.session['of_booking_wizard_id'] = False
                return self._search_slots(template_id, service_id, partner_id, from_date, search_more=search_more)
            compute = 'more'
            request.session['search_slot_result_nb'] += 10
        else:
            employee_ids = request.env['ir.values'].sudo().with_context(force_company=booking_company_id).get_default(
                'of.intervention.settings', 'booking_employee_ids') or []
            day_ids = request.env['ir.values'].sudo().with_context(force_company=booking_company_id).get_default(
                'of.intervention.settings', 'booking_opened_day_ids') or []
            search_mode = request.env['ir.values'].sudo().with_context(force_company=booking_company_id).get_default(
                'of.intervention.settings', 'booking_search_mode')
            if template_id:
                template = request.env['of.planning.intervention.template'].browse(template_id)
                task = template.sudo().tache_id
            else:
                service = request.env['of.service'].browse(service_id)
                task = service.sudo().tache_id
            wizard_vals = {
                'company_id': booking_company_id,
                'partner_id': partner_id,
                'partner_address_id': partner_id,
                'tache_id': task.id,
                'date_recherche_debut': from_date,
                'duree': task.duree,
                'day_ids': [(6, 0, day_ids)],
                'search_mode': search_mode,
                'search_type': search_type,
            }
            wizard = request.env['of.tournee.rdv'].with_context(from_portal=True).create(wizard_vals)
            wizard.sudo().pre_employee_ids = [(6, 0, employee_ids)]
            wizard._onchange_date_recherche_debut()
            request.session['of_booking_wizard_id'] = wizard.id
            compute = 'new'
            request.session['search_slot_result_nb'] = 10

        web_slots = []

        # Nombre de jours max ouverts à la réservation
        max_days = request.env['ir.values'].sudo().with_context(force_company=booking_company_id).get_default(
            'of.intervention.settings', 'booking_open_days_number')
        max_search_date = (datetime.today() + timedelta(days=max_days)).strftime('%Y-%m-%d')

        if compute == 'new':
            search_end_date = datetime.strptime(from_date, '%Y-%m-%d') + timedelta(days=14)
            wizard.date_recherche_fin = min(search_end_date.strftime('%Y-%m-%d'), max_search_date)
            wizard.compute(sudo=True, mode=compute)

        valid_lines = self._filter_slots(
            wizard.planning_ids, search_type, max_search_criteria, allow_empty_days, wizard.duree)

        # Tenter jusqu'à avoir au moins 10 résultats ou ne plus être dans les jours ouverts à la réservation
        while len(valid_lines) < request.session['search_slot_result_nb'] and \
                wizard.date_recherche_fin < max_search_date:
            new_search_start_date = datetime.strptime(wizard.date_recherche_fin, "%Y-%m-%d") + timedelta(days=1)
            new_search_end_date = new_search_start_date + timedelta(days=6)
            wizard.date_recherche_debut = new_search_start_date.strftime('%Y-%m-%d')
            wizard.date_recherche_fin = min(new_search_end_date.strftime('%Y-%m-%d'), max_search_date)
            wizard.compute(sudo=True, mode='more')
            valid_lines = self._filter_slots(
                wizard.planning_ids, search_type, max_search_criteria, allow_empty_days, wizard.duree)

        if valid_lines:
            web_slots = wizard.build_website_creneaux(valid_lines, mode='half_day')
            # Keep slots of the same day together
            slots_nb = request.session['search_slot_result_nb']
            if len(web_slots) > slots_nb and web_slots[slots_nb - 1].description == "Matin" and \
                    web_slots[slots_nb - 1].name == web_slots[slots_nb].name:
                slots_nb += 1
            web_slots = web_slots[0:slots_nb]
        else:
            web_slots = []

        no_more_search = (wizard.date_recherche_fin >= max_search_date)

        return [web_slots, not no_more_search]

    def _filter_slots(self, rdv_lines, search_type, max_search_criteria, allow_empty_days, duration):
        valid_lines = rdv_lines.filtered(lambda p: p.disponible)
        tz = pytz.timezone(request._context.get('tz', "Europe/Paris"))

        if search_type == 'duration':
            valid_lines = valid_lines.filtered(lambda line: line.duree_utile <= max_search_criteria)
        else:
            valid_lines = valid_lines.filtered(lambda line: line.distance_utile <= max_search_criteria)

        if not allow_empty_days:
            # Check that employee has at least one intervention on the same day
            valid_lines = valid_lines.filtered(lambda line: line.sudo().tour_id.intervention_ids)

        # Check website hours
        for valid_line in valid_lines:
            curr_employee = valid_line.employee_id.sudo()
            if curr_employee.of_website_segment_ids:
                website_daily_hours = curr_employee.get_horaires_date(valid_line.date, seg_type='website')
                for web_hours_slot in website_daily_hours[curr_employee.id]:
                    if float_compare(web_hours_slot[0], valid_line.date_flo, 5) != 1:
                        if float_compare(web_hours_slot[1], valid_line.date_flo_deadline, 5) != -1:
                            # Web hours slot include all free slot, we break
                            break
                        else:
                            # Web hours slot end hour is lower than free slot end hour,
                            # test if there is enough time for the task
                            if float_compare(web_hours_slot[1] - valid_line.date_flo, duration, 5) != -1:
                                # We adapt free slot
                                end_date = datetime.combine(
                                    datetime.strptime(valid_line.date, "%Y-%m-%d"), datetime.min.time()) \
                                    + timedelta(hours=web_hours_slot[1])
                                end_date = tz.localize(end_date, is_dst=None).astimezone(pytz.utc)
                                valid_line.write({
                                    'fin_dt': end_date,
                                    'date_flo_deadline': web_hours_slot[1],
                                    'description': "%s-%s" % tuple(hours_to_strs(
                                        valid_line.date_flo, web_hours_slot[1])),
                                })
                                break
                    else:
                        # Web hours slot start hour is greater than free slot start hour
                        # test if web hour slot is long enough for the task
                        if float_compare(
                                min(web_hours_slot[1], valid_line.date_flo_deadline) - web_hours_slot[0],
                                duration, 5) != -1:
                            # We adapt free slot
                            start_date = datetime.combine(
                                datetime.strptime(valid_line.date, "%Y-%m-%d"), datetime.min.time()) \
                                + timedelta(hours=web_hours_slot[0])
                            start_date = tz.localize(start_date, is_dst=None).astimezone(pytz.utc)
                            vals = {
                                'debut_dt': start_date,
                                'date_flo': web_hours_slot[0],
                                'description': "%s-%s" % tuple(
                                    hours_to_strs(web_hours_slot[0], valid_line.date_flo_deadline)),
                            }
                            if float_compare(web_hours_slot[1], valid_line.date_flo_deadline, 5) == -1:
                                end_date = datetime.combine(
                                    datetime.strptime(valid_line.date, "%Y-%m-%d"), datetime.min.time()) \
                                    + timedelta(hours=web_hours_slot[1])
                                end_date = tz.localize(end_date, is_dst=None).astimezone(pytz.utc)
                                vals.update({
                                    'fin_dt': end_date,
                                    'date_flo_deadline': web_hours_slot[1],
                                    'description': "%s-%s" % tuple(hours_to_strs(web_hours_slot[0], web_hours_slot[1])),
                                })
                            valid_line.write(vals)
                            break
                else:
                    valid_lines -= valid_line

        return valid_lines

    def _create_update_intervention(self, intervention, template, service, partner, slot):
        created = False
        # fonctionnement basique pour la création : si le créneau backend sélectionné a été rempli entre temps
        # et que le créneau frontend est connecté à d'autre créneaux backend, essayer un autre créneau backend
        while not created and slot.planning_ids:
            backend_slot = slot.planning_ids.sorted(lambda p: (p.dist_prec, p.dist_ortho_prec))[0]
            backend_slot.button_select(sudo=True)

            vals = self._get_intervention_vals(slot, backend_slot, template, service, partner)
            try:
                if intervention:
                    intervention.write(vals)
                else:
                    intervention = request.env['of.planning.intervention'].sudo().create(vals)
                intervention.onchange_company_id()
                intervention.with_context(of_import_service_lines=True)._onchange_service_id()
                intervention.with_context(of_import_service_lines=True)._onchange_tache_id()
                intervention.with_context(of_import_service_lines=True).onchange_template_id()
                if intervention.line_ids:
                    intervention.line_ids.compute_taxes()
                # mettre à jour le nom du RDV
                intervention.with_context(from_portal=True)._onchange_address_id()
                created = True
            except Exception as e:
                backend_slot.unlink()
                _logger.warning(u"Erreur à la création de RDV depuis le portail: %s", e.message)
        # si le créneau front n'est plus connecté à un créneau backend, le supprimer
        if not slot.planning_ids:
            slot.unlink()
        return intervention

    def _get_intervention_vals(self, slot, backend_slot, template, service, partner):
        tz = pytz.timezone('Europe/Paris')

        default_state = request.env['ir.values'].sudo().with_context(
            force_company=self._get_company_id()).get_default(
                'of.intervention.settings', 'booking_intervention_state') or 'draft'

        description = ""
        if request.params.get('comment'):
            description = u"Commentaires additionnels du client : %s" % request.params.get('comment')

        if template:
            template_id = template.id
            service_id = False
            task = template.tache_id
        else:
            template_id = service.template_id and service.template_id.id
            service_id = service.id
            task = service.tache_id

        partner_id = partner.id
        if request.env.uid != request.website.user_id.id:
            partner_id = request.env.user.partner_id.id

        vals = {
            'name': u"Intervention web",
            'partner_id': partner_id,
            'address_id': partner.id,
            'template_id': template_id,
            'service_id': service_id,
            'tache_id': task.id,
            'flexible': task.flexible,
            'employee_ids': [(4, backend_slot.employee_id.id, 0)],
            'duree': task.duree,
            'company_id': self._get_company_id(),
            'state': default_state,
            'fiscal_position_id': task.fiscal_position_id.id or False,
            'verif_dispo': True,
            'origin_interface': u"Portail web",
            'website_create': True,
            'description': description,
        }

        # Le créneau de l'employé peut commencer avant le début d'aprem,
        # on fait donc un max pour s'assurer que le RDV soit pris l'aprem
        if slot.name.lower() == 'après-midi':
            afternoon_start_hour = 13.0  # -> à récupérer depuis de la config en backend?
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
