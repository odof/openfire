# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import api, models, fields
from odoo.addons.of_utils.models.of_utils import hours_to_strs


class TourPlanningOptimizationWizard(models.TransientModel):
    _name = 'tour.planning.optimization.wizard'
    _description = 'Tour Planning Optimization Wizard'

    @api.model
    def default_get(self, fields_list):
        res = super(TourPlanningOptimizationWizard, self).default_get(fields_list)
        if not self._context.get('default_tour_id') and self.env.context.get('active_model') == 'of.planning.tournee' \
                and self.env.context.get('active_id'):
            res['tour_id'] = self.env.context.get('active_id')
        return res

    tour_id = fields.Many2one(comodel_name='of.planning.tournee', string='Tour', required=True)
    optimization_mode = fields.Selection(
        selection=[('duration', 'Duration'), ('distance', 'Distance')], string='Optimization Mode', required=True,
        default='duration')
    include_fixed_appointments = fields.Boolean(string='Include Fixed Appointments', default=True)
    opt_tour_line_ids = fields.One2many(
        comodel_name='tour.planning.optimization.line.wizard', inverse_name='wizard_id', string='Lines to optimize')

    @api.onchange('tour_id')
    @api.multi
    def initialize(self):
        optimization_line_obj = self.env['tour.planning.optimization.line.wizard']
        for wizard in self:
            wizard.opt_tour_line_ids = [(5, 0, 0)]
            lines_values = []
            for tour_line in wizard.tour_id.tour_line_ids:
                intervention = tour_line.intervention_id
                date_intervention = fields.Datetime.context_timestamp(
                    intervention, fields.Datetime.from_string(intervention.date)).strftime('%d/%m/%Y')
                old_time_slot = '%s %s - %s' % (
                    date_intervention, intervention.heure_debut_str, intervention.heure_fin_str)
                new_line = optimization_line_obj.new({
                    'tour_line_id': tour_line.id,
                    'intervention_id': intervention.id,
                    'sequence': tour_line.sequence,
                    'old_time_slot': old_time_slot,
                    'new_time_slot': False,
                    'duration': False,
                    'distance': False,
                })
                lines_values.append((0, 0, new_line._convert_to_write(new_line._cache)))
            wizard.opt_tour_line_ids = lines_values

    @api.multi
    def action_optimize(self):
        self.ensure_one()
        print "Optimizing tour %s" % self.tour_id.name
        print "Optimizing tour %s" % self.tour_id.name
        print "Optimizing tour %s" % self.tour_id.name
        res = self.tour_id._send_osrm_trip_request()
        print res
        SDSDSDSD


class TourPlanningOptimizationLineWizard(models.TransientModel):
    _name = 'tour.planning.optimization.line.wizard'

    wizard_id = fields.Many2one(comodel_name='tour.planning.optimization.wizard', string='Wizard')
    tour_line_id = fields.Many2one(comodel_name='of.planning.tour.line', string='Tour Line')
    intervention_id = fields.Many2one(comodel_name='of.planning.intervention', string='Intervention')
    flexible = fields.Boolean(string='Flexible', related='intervention_id.flexible')
    workers_names = fields.Char(string='Workers', compute='_compute_workers_names')
    old_time_slot = fields.Char(string='Old Time Slot')
    new_time_slot = fields.Char(string='New Time Slot')
    duration = fields.Float(string='Duration')
    distance = fields.Float(string='Distance')

    @api.multi
    def _compute_workers_names(self):
        for line in self:
            line.workers_names = ', '.join(line.intervention_id.employee_ids.mapped('name'))
