# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import json

from odoo import http
from odoo.http import request


class OFCalculationController(http.Controller):

    def _cleanup_session(self):
        if 'heat_loss_id' in request.session:
            del request.session['heat_loss_id']
        if 'mail_attempt' in request.session:
            del request.session['mail_attempt']

    @http.route('/calcul_deperdition_chaleur', type='http', auth="public", methods=['GET', 'POST'], website=True)
    def heat_loss_calculation_form(self, **kwargs):
        heat_loss_obj = request.env['of.calculation.heat.loss']
        altitude_obj = request.env['of.calculation.altitude']
        construction_date_obj = request.env['of.calculation.construction.date']
        construction_type_obj = request.env['of.calculation.construction.type']
        surface_obj = request.env['of.calculation.surface']
        coef_obj = request.env['of.calculation.fuel.coef']
        zip_better_obj = request.env['res.better.zip']

        heat_loss_id = request.session.get('heat_loss_id')
        heat_loss = heat_loss_obj.sudo().browse(heat_loss_id).exists() if heat_loss_id else None

        if kwargs and kwargs.get("zip_id"):
            zip_better_obj = zip_better_obj.search(
                [('display_name', '=', kwargs["zip_id"])])
            if zip_better_obj:
                kwargs['zip_id'] = zip_better_obj.id
                kwargs['display_name'] = zip_better_obj.display_name
                kwargs['partner_zip'] = zip_better_obj.name
                kwargs['partner_city'] = zip_better_obj.city
                kwargs['partner_state_id'] = zip_better_obj.state_id.id

        if request.httprequest.method == 'POST':
            if heat_loss:
                heat_loss.write(kwargs)
            elif kwargs:
                country = request.env['res.country'].search([('code', '=', 'FR')])
                kwargs['partner_country_id'] = country.id
                heat_loss = heat_loss_obj.sudo().create(kwargs)

            if heat_loss:
                heat_loss.button_compute_estimated_power()
                request.session['heat_loss_id'] = heat_loss.id
        values = {
            'altitudes': altitude_obj.search([]),
            'construction_dates': construction_date_obj.search([]),
            'better_g_list': heat_loss_obj.get_construction_date_for_better_g(),
            'construction_types': construction_type_obj.search([]),
            'wall_surfaces': surface_obj.search([('surface_type', '=', 'wall')]),
            'roof_surfaces': surface_obj.search([('surface_type', '=', 'roof')]),
            'floor_surfaces': surface_obj.search([('surface_type', '=', 'floor')]),
            'fuel_coefs': coef_obj.search([]),
        }
        logement_principal = request.env.ref('of_calculation_heat_loss.construction_type_1', raise_if_not_found=False)
        if logement_principal and logement_principal in values['construction_types']:
            values['construction_type_id'] = logement_principal
        if heat_loss:
            fields_dict = {}
            for key in heat_loss.fields_get():
                fields_dict[key] = heat_loss[key]
            values.update(fields_dict)
            values.update({
                'fuel_consumption_values': json.dumps({
                    'names': heat_loss.fuel_consumption_ids.mapped('fuel_id.name'),
                    'costs': heat_loss.fuel_consumption_ids.mapped('fuel_cost'),
                    # :todo: Intégrer la couleur dans les carburants
                    'colors': ["#79c5b1", "pink", "orange", "green", "#6d4c41", "#90bae9"],
                }),

            })
        if request.session.get('mail_attempt') and heat_loss:
            if heat_loss.mailing_attempt == 'success':
                message = u"Le compte-rendu a bien été envoyé à l'adresse : %s" % heat_loss.pro_partner_id.email
            else:
                message = u"Désolé, il semble que l'adresse que vous avez renseignée est introuvable ou incorrecte. " \
                          u"Veuillez réessayer avec une adresse mail valide."
            values['mailing_attempt_message'] = message

        return request.render('of_website_calculation_heat_loss.heat_loss_calculation_form', values)

    @http.route('/get_heat_loss_altitude_ids_from_zip', type='json', auth="public", methods=['POST'], website=True)
    def get_heat_loss_altitude_ids_from_zip(self, zip, **args):
        return request.env['of.calculation.heat.loss'].get_altitude_ids_from_zip(zip)

    @http.route('/get_heat_loss_fuel_coef', type='json', auth="public", methods=['POST'], website=True)
    def get_heat_loss_fuel_coef(self, coef_id, **args):
        return request.env['of.calculation.fuel.coef'].browse(coef_id).sudo().coef

    @http.route('/get_heat_loss_pdf', type='http', auth="public", methods=['POST'], website=True)
    def get_heat_loss_pdf(self, **kwargs):
        heat_loss_obj = request.env['of.calculation.heat.loss']
        heat_loss_id = request.session.get('heat_loss_id')
        heat_loss = heat_loss_obj.sudo().browse(heat_loss_id).exists() if heat_loss_id else None

        try:
            heat_loss.write(kwargs)
            heat_loss.with_context(heat_loss_mail_attempt=True).send_calculation()
        except Exception:
            heat_loss.write({'mailing_attempt': 'failed'})

        request.session['mail_attempt'] = True

        return self.heat_loss_calculation_form()

    @http.route('/calcul_deperdition_chaleur_new', type='http', auth="public", methods=['GET', 'POST'], website=True)
    def heat_loss_calculation_form_new(self, **kwargs):
        self._cleanup_session()
        return self.heat_loss_calculation_form(**kwargs)
