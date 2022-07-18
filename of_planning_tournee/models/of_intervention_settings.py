# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class OfInterventionSettings(models.TransientModel):
    _inherit = 'of.intervention.settings'

    @api.model_cr_context
    def _auto_init(self):
        res = super(OfInterventionSettings, self)._auto_init()
        if not self.env['ir.values'].get_default('of.intervention.settings', 'company_choice'):
            self.env['ir.values'].sudo().set_default(
                'of.intervention.settings', 'company_choice', 'contact')
        if not self.env['ir.values'].get_default('of.intervention.settings', 'planning_results'):
            self.env['ir.values'].sudo().set_default(
                'of.intervention.settings', 'planning_results', True)
        if not self.env['ir.values'].get_default('of.intervention.settings', 'number_of_results'):
            self.env['ir.values'].sudo().set_default(
                'of.intervention.settings', 'number_of_results', 10)
        if not self.env['ir.values'].get_default('of.intervention.settings', 'show_next_available_time_slots'):
            self.env['ir.values'].sudo().set_default(
                'of.intervention.settings', 'show_next_available_time_slots', False)
        if not self.env['ir.values'].get_default('of.intervention.settings', 'search_type'):
            self.env['ir.values'].sudo().set_default(
                'of.intervention.settings', 'search_type', 'distance')
        if not self.env['ir.values'].get_default('of.intervention.settings', 'slots_display_mode'):
            self.env['ir.values'].sudo().set_default(
                'of.intervention.settings', 'slots_display_mode', 'list')
        return res

    # Time slots research
    planning_results = fields.Boolean(string="Planning results", default=True, help="Show results in the planning")
    number_of_results = fields.Integer(
        string='Number of results', default=10, help="Number of results to show in the planning. (Max : 30)")
    show_next_available_time_slots = fields.Boolean(
        string="Show next avaibable time slots", default=False, help="Show next available time slots in the planning")
    search_type = fields.Selection(
        string="Search type", selection=[('distance', 'Distance (km)'), ('duration', 'Duration (min)')], required=True,
        default='distance')
    slots_display_mode = fields.Selection(
        string="Default mode for the display of the results", selection=[('list', 'List'), ('calendar', 'Calendar')],
        default='list', required=True)

    @api.constrains('number_of_results')
    def _check_number_of_results(self):
        if self.number_of_results > 30:
            raise ValidationError(_("The Number of results can't exceed more than 30"))

    @api.multi
    def set_planning_results(self):
        return self.env['ir.values'].sudo().set_default(
            'of.intervention.settings', 'planning_results', self.planning_results)

    @api.multi
    def set_number_of_results(self):
        return self.env['ir.values'].sudo().set_default(
            'of.intervention.settings', 'number_of_results', self.number_of_results)

    @api.multi
    def set_show_next_available_time_slots(self):
        return self.env['ir.values'].sudo().set_default(
            'of.intervention.settings', 'show_next_available_time_slots', self.show_next_available_time_slots)

    @api.multi
    def set_search_type(self):
        return self.env['ir.values'].sudo().set_default(
            'of.intervention.settings', 'search_type', self.search_type)

    @api.multi
    def set_slots_display_mode(self):
        return self.env['ir.values'].sudo().set_default(
            'of.intervention.settings', 'slots_display_mode', self.slots_display_mode)
