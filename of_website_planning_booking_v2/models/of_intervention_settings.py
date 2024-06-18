# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, models, fields
from odoo.addons.of_planning_tournee.models.of_intervention_settings import SELECTION_SEARCH_TYPES
from odoo.addons.of_planning_tournee.models.of_intervention_settings import SELECTION_SEARCH_MODES


class OFInterventionSettings(models.TransientModel):
    _inherit = 'of.intervention.settings'

    @api.model
    def _auto_init(self):
        super(OFInterventionSettings, self)._auto_init()
        if self.env['ir.values'].get_default('of.intervention.settings', 'booking_opened_day_ids') is None:
            self.env['ir.values'].set_default(
                'of.intervention.settings', 'booking_opened_day_ids', self._default_opened_day_ids())
        if self.env['ir.values'].get_default('of.intervention.settings', 'booking_search_mode') is None:
            self.env['ir.values'].set_default('of.intervention.settings', 'booking_search_mode', 'oneway')
        if self.env['ir.values'].get_default('of.intervention.settings', 'booking_search_type') is None:
            self.env['ir.values'].set_default('of.intervention.settings', 'booking_search_type', 'distance')
        if self.env['ir.values'].get_default('of.intervention.settings', 'booking_search_max_criteria') is None:
            self.env['ir.values'].set_default('of.intervention.settings', 'booking_search_max_criteria', 20)

    def _default_opened_day_ids(self):
        days = self.env['of.jours'].search([('numero', '<', 6)], order='numero')
        res = [day.id for day in days]
        return res

    booking_opened_day_ids = fields.Many2many(
        comodel_name='of.jours', string=u"Jours ouverts", default=_default_opened_day_ids)
    booking_employee_ids = fields.Many2many(
        comodel_name='hr.employee', relation='of_intervention_settings_booking_employee_rel',
        string=u"Techniciens disponibles", domain=[('of_est_intervenant', '=', True)])
    booking_search_mode = fields.Selection(
        selection=SELECTION_SEARCH_MODES, string=u"Mode de recherche", required=True)
    booking_search_type = fields.Selection(
        selection=SELECTION_SEARCH_TYPES, string=u"Type de recherche", required=True)
    booking_search_max_criteria = fields.Integer(string=u"Critèe de recherche max", required=True)

    @api.multi
    def set_booking_opened_day_ids_defaults(self):
        return self.env['ir.values'].sudo().set_default(
            'of.intervention.settings', 'booking_opened_day_ids', self.booking_opened_day_ids.ids)

    @api.multi
    def set_booking_employee_ids_defaults(self):
        return self.env['ir.values'].sudo().set_default(
            'of.intervention.settings', 'booking_employee_ids', self.booking_employee_ids.ids)

    @api.multi
    def set_booking_search_mode_defaults(self):
        return self.env['ir.values'].sudo().set_default(
            'of.intervention.settings', 'booking_search_mode', self.booking_search_mode)

    @api.multi
    def set_booking_search_types_defaults(self):
        return self.env['ir.values'].sudo().set_default(
            'of.intervention.settings', 'booking_search_type', self.booking_search_type)

    @api.multi
    def set_booking_search_max_criteria_defaults(self):
        return self.env['ir.values'].sudo().set_default(
            'of.intervention.settings', 'booking_search_max_criteria', self.booking_search_max_criteria)
