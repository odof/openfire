# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

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

    @api.model
    def _default_day_ids(self):
        # monday to friday as default
        days = self.env['of.jours'].search([('numero', 'in', (1, 2, 3, 4, 5))], order="numero")
        return [day.id for day in days]

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
    # Tour planning
    nbr_days_tour_creation = fields.Integer(
        string='Tours // Create Tours over __ days', default=30, required=True,
        help="Defines the number of days on which to create the routes for each employee whose work hours "
        "are defined. Maximum: 180 days.")
    tour_employee_ids = fields.Many2many(
        comodel_name='hr.employee', relation='intervention_settings_tour_employee_rel', string="Tours // Employees",
        help="Create tours for these employees only", default=False)
    tour_day_ids = fields.Many2many(
        comodel_name='of.jours', relation='intervention_settings_tour_days_rel', string="Tours // Days",
        help="Create tours for these days only", default=lambda self: self._default_day_ids())
    group_of_planning_tournee_manual_creation = fields.Boolean(
        string=u"(OF) Création manuelle des tournées autorisée",
        implied_group='of_planning_tournee.group_planning_tournee_manual_creation', group='base.group_user',
        help=u"Rend disponible la création dans la vue des tournées.")

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

    @api.constrains('nbr_days_tour_creation')
    def _check_nbr_days_tour_creation(self):
        if 1 <= self.nbr_days_tour_creation > 180:
            raise ValidationError(_("The number of days for the tours creation must be positive and can't exceed 180"))

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

    @api.multi
    def set_nbr_days_tour_creation(self):
        return self.env['ir.values'].sudo().set_default(
            'of.intervention.settings', 'nbr_days_tour_creation', self.nbr_days_tour_creation)

    @api.multi
    def set_tour_employee_ids(self):
        IrValues = self.env['ir.values'].sudo()
        return IrValues.set_default('of.intervention.settings', 'tour_employee_ids', self.tour_employee_ids.ids)

    @api.multi
    def set_tour_day_ids(self):
        IrValues = self.env['ir.values'].sudo()
        return IrValues.set_default('of.intervention.settings', 'tour_day_ids', self.tour_day_ids.ids)
