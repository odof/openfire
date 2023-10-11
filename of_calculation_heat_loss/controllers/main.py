# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import http
from odoo.http import request


class OFCalculationController(http.Controller):

    @http.route('/calcul_deperdition_chaleur', type='http', auth="public", website=True)
    def heat_loss_calculation_form(self, heat_loss_id=None, **kwargs):
        heat_loss_obj = request.env['of.calculation.heat.loss']
        altitude_obj = request.env['of.calculation.altitude']
        construction_date_obj = request.env['of.calculation.construction.date']
        construction_type_obj = request.env['of.calculation.construction.type']
        surface_obj = request.env['of.calculation.surface']

        values = {
            'altitudes': altitude_obj.search([]),
            'construction_dates': construction_date_obj.search([]),
            'better_g_list': heat_loss_obj.get_construction_date_for_better_g(),
            'construction_types': construction_type_obj.search([]),
            'wall_surfaces': surface_obj.search([('surface_type', '=', 'wall')]),
            'roof_surfaces': surface_obj.search([('surface_type', '=', 'roof')]),
            'floor_surfaces': surface_obj.search([('surface_type', '=', 'floor')]),
        }
        heat_loss_id = request.session.get('heat_loss_id')
        heat_loss = heat_loss_obj.sudo().browse(heat_loss_id).exists() if heat_loss_id else None
        if heat_loss:
            fields_dict = {}
            for key in heat_loss.fields_get():
                fields_dict[key] = heat_loss[key]
            values.update(fields_dict)

        return http.request.render('of_calculation_heat_loss.heat_loss_calculation_form', values)

    @http.route('/create_heat_loss_calculation', type='http', auth="public", methods=['POST'], website=True)
    def create_heat_loss_calculation(self, **kwargs):
        heat_loss_obj = request.env['of.calculation.heat.loss']
        heat_loss_id = request.session.get('heat_loss_id')
        heat_loss = heat_loss_obj.sudo().browse(heat_loss_id).exists() if heat_loss_id else None

        if heat_loss:
            heat_loss.write(kwargs)
        else:
            heat_loss = heat_loss_obj.sudo().create(kwargs)

        heat_loss.button_compute_estimated_power()
        request.session['heat_loss_id'] = heat_loss.id

        return request.redirect('/calcul_deperdition_chaleur')

    @http.route('/get_heat_loss_pdf', type='http', auth="public", methods=['POST'], website=True)
    def get_heat_loss_pdf(self, **kwargs):
        heat_loss_obj = request.env['of.calculation.heat.loss']
        heat_loss_id = request.session.get('heat_loss_id')
        heat_loss = heat_loss_obj.sudo().browse(heat_loss_id).exists() if heat_loss_id else None

        heat_loss.write(kwargs)
        heat_loss.send_calculation()

        return request.redirect('/calcul_deperdition_chaleur')
