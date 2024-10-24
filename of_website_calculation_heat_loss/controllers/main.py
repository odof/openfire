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
        if 'display_altitude' in request.session:
            del request.session['display_altitude']

    def send_email(self, heat_loss, **kwargs):
        try:
            heat_loss.write(kwargs)
            heat_loss.with_context(heat_loss_mail_attempt=True).send_calculation()
        except Exception:
            heat_loss.write({'mailing_attempt': 'failed'})
        request.session['mail_attempt'] = True

    def address_fields(self):
        return ['zip_id', 'partner_zip', 'partner_city', 'partner_state_id', 'partner_street']

    def update_heat_loss(self, heat_loss, **kwargs):
        if heat_loss:
            heat_loss.write(kwargs)
        elif kwargs:
            country = request.env['res.country'].search([('code', '=', 'FR')])
            kwargs['partner_country_id'] = country.id
            heat_loss = heat_loss.sudo().create(kwargs)
            heat_loss.geolocalize()
        if any(kwargs[key] != heat_loss[key] for key in self.address_fields()):
            heat_loss.geolocalize()
        return heat_loss

    @http.route('/calcul_deperdition_chaleur', type='http', auth="public", methods=['GET', 'POST'], website=True)
    def heat_loss_calculation_form(self, **kwargs):
        env = request.env
        heat_loss_obj = env['of.calculation.heat.loss']
        altitude_obj = env['of.calculation.altitude']
        department_obj = env['of.calculation.department']
        construction_date_obj = env['of.calculation.construction.date']
        construction_type_obj = env['of.calculation.construction.type']
        surface_obj = env['of.calculation.surface']
        button_pressed = kwargs.pop('button_id', False)
        coef_obj = env['of.calculation.fuel.coef']
        better_zip_obj = env['res.better.zip']
        display_altitude = request.session.get('display_altitude', False)

        if button_pressed:
            env['of.calculation.statistics'].sudo().add_button_click(button_pressed)
        if button_pressed == 'reload':
            self._cleanup_session()
        heat_loss_id = request.session.get('heat_loss_id')
        heat_loss = heat_loss_obj.sudo().browse(heat_loss_id).exists() if heat_loss_id else None

        has_errors = {}
        if kwargs and kwargs.get('zip_id'):
            better_zip = better_zip_obj.search(
                [('display_name', 'ilike', kwargs['zip_id'])], limit=1)
            if better_zip:
                kwargs['zip_id'] = better_zip.id
                kwargs['display_name'] = better_zip.display_name
                kwargs['partner_zip'] = better_zip.name
                kwargs['partner_city'] = better_zip.city
                kwargs['partner_state_id'] = better_zip.state_id.id
            else:
                has_errors['zip_id'] = True
                del kwargs['zip_id']

        altitudes = altitude_obj.search([])
        if not has_errors:
            heat_loss = heat_loss_obj.sudo().browse(heat_loss_id).exists() if heat_loss_id else heat_loss_obj
            if button_pressed == 'mail':
                self.send_email(heat_loss=heat_loss, **kwargs)
            if button_pressed == 'validate':
                heat_loss = self.update_heat_loss(heat_loss=heat_loss, **kwargs)
            if heat_loss and not heat_loss.altitude_id:
                display_altitude = has_errors['altitude'] = True
                request.session['display_altitude'] = True
                department = department_obj.search([('code', '=', heat_loss.partner_id.zip[:2])], limit=1)
                if department:
                    altitudes = department.base_temperature_id.line_ids.mapped('altitude_id')
        if heat_loss:
            request.session['heat_loss_id'] = heat_loss.id
            if not has_errors:
                heat_loss.button_compute_estimated_power()

        values = {
            'altitudes': altitudes,
            'construction_dates': construction_date_obj.search([]),
            'better_g_list': heat_loss_obj.get_construction_date_for_better_g(),
            'construction_types': construction_type_obj.search([]),
            'wall_surfaces': surface_obj.search([('surface_type', '=', 'wall')]),
            'roof_surfaces': surface_obj.search([('surface_type', '=', 'roof')]),
            'floor_surfaces': surface_obj.search([('surface_type', '=', 'floor')]),
            'fuel_coefs': coef_obj.search([]),
            'error_dict': has_errors,
            'display_altitude': display_altitude,
        }
        if has_errors:
            fields_dict = {}
            fields_get = heat_loss_obj.fields_get()
            for key in kwargs:
                if key in fields_get:
                    if fields_get[key]['type'] == 'many2one':
                        fields_dict[key] = env[fields_get[key]['relation']].browse(int(kwargs[key] or 0)).exists()
                    else:
                        fields_dict[key] = kwargs[key]
            values.update(fields_dict)
        logement_principal = env.ref('of_calculation_heat_loss.construction_type_1', raise_if_not_found=False)
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
