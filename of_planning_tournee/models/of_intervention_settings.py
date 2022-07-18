# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


SELECTION_SEARCH_TYPES = [
    ('distance', "Distance (km)"),
    ('duration', "Duration (min)"),
]

SELECTION_SEARCH_MODES = [
    ('oneway', "One way"),
    ('return', "Return"),
    ('round_trip', "Round trip"),
    ('oneway_or_return', "One way or Return"),
    ('oneway_am_return_pm', "One way if morning / Return if afternoon"),
]


class OfInterventionSettings(models.TransientModel):
    _inherit = 'of.intervention.settings'

    @api.model_cr_context
    def _auto_init(self):
        res = super(OfInterventionSettings, self)._auto_init()
        ir_values_obj = self.env['ir.values'].sudo()
        if not ir_values_obj.get_default('of.intervention.settings', 'company_choice'):
            ir_values_obj.set_default('of.intervention.settings', 'company_choice', 'contact')
        if not ir_values_obj.get_default('of.intervention.settings', 'number_of_results'):
            ir_values_obj.set_default('of.intervention.settings', 'number_of_results', 10)
        if not ir_values_obj.get_default('of.intervention.settings', 'show_next_available_time_slots'):
            ir_values_obj.set_default('of.intervention.settings', 'show_next_available_time_slots', False)
        if not ir_values_obj.get_default('of.intervention.settings', 'search_type'):
            ir_values_obj.set_default('of.intervention.settings', 'search_mode', 'oneway_or_return')
        if not ir_values_obj.get_default('of.intervention.settings', 'search_type'):
            ir_values_obj.set_default('of.intervention.settings', 'search_type', 'distance')
        if not ir_values_obj.get_default('of.intervention.settings', 'slots_display_mode'):
            ir_values_obj.set_default('of.intervention.settings', 'slots_display_mode', 'list')
        return res

    # Time slots research
    number_of_results = fields.Integer(
        string="Number of results", default=10, help="Number of results to show in the planning. (Max : 30)")
    show_next_available_time_slots = fields.Boolean(
        string="Show next avaibable time slots", default=False,
        help="Allows you to display the table of available time slots by date in the planning insert")
    search_mode = fields.Selection(
        string="Search mode", selection=SELECTION_SEARCH_MODES, required=True, default='oneway_or_return')
    search_type = fields.Selection(
        string="Search type", selection=SELECTION_SEARCH_TYPES, required=True, default='distance')
    slots_display_mode = fields.Selection(
        string="Default mode for displaying results", selection=[('list', "List"), ('calendar', "Calendar")],
        default='list', required=True)
    enable_quick_scheduling = fields.Boolean(
        string="Enable quick scheduling", default=False,
        help="Will trigger auto search from contacts/installed parks/tasks/etc. like for intervention requests")
    default_planning_task_id = fields.Many2one(comodel_name='of.planning.tache', string="Default task for searching")

    @api.onchange('enable_quick_scheduling')
    def _onchange_enable_quick_scheduling(self):
        if not self.enable_quick_scheduling:
            self.update({
                'default_planning_task_id': False,
            })

    @api.constrains('number_of_results')
    def _check_number_of_results(self):
        if 1 <= self.number_of_results > 30:
            raise ValidationError(_("The Number of results must be positive and can't exceed 30."))

    @api.multi
    def set_enable_quick_scheduling(self):
        return self.env['ir.values'].sudo().set_default(
            'of.intervention.settings', 'enable_quick_scheduling', self.enable_quick_scheduling)

    @api.multi
    def set_number_of_results(self):
        return self.env['ir.values'].sudo().set_default(
            'of.intervention.settings', 'number_of_results', self.number_of_results)

    @api.multi
    def set_show_next_available_time_slots(self):
        return self.env['ir.values'].sudo().set_default(
            'of.intervention.settings', 'show_next_available_time_slots', self.show_next_available_time_slots)

    @api.multi
    def set_search_mode(self):
        return self.env['ir.values'].sudo().set_default('of.intervention.settings', 'search_mode', self.search_mode)

    @api.multi
    def set_search_type(self):
        return self.env['ir.values'].sudo().set_default('of.intervention.settings', 'search_type', self.search_type)

    @api.multi
    def set_slots_display_mode(self):
        return self.env['ir.values'].sudo().set_default(
            'of.intervention.settings', 'slots_display_mode', self.slots_display_mode)

    @api.multi
    def set_default_planning_task_id(self):
        return self.env['ir.values'].sudo().set_default(
            'of.intervention.settings', 'default_planning_task_id', self.default_planning_task_id.id or False)
