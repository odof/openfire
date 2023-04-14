# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import api, models, fields, _


class OFTourPlanningReorganizationWizard(models.TransientModel):
    _name = 'of.tour.planning.reorganization.wizard'
    _description = "Tour Planning Reorganization Wizard"
    _inherit = 'of.tour.planning.wizard.mixin'

    line_ids = fields.One2many(
        comodel_name='of.tour.planning.reorganization.line.wizard', inverse_name='wizard_id',
        string="Lines to reorganize")

    @api.multi
    def _update_reorganization_lines_date(self, reorganized_tour_lines, wizard_line_mapping):
        """Update the wizard lines with the new time slot created by the optimization"""
        self.ensure_one()

        # Get the new values for the wizard lines from the optimized tour lines
        values_by_lines = self._get_new_slot_data_by_lines(
            reorganized_tour_lines, wizard_line_mapping, time_slot_label=False)
        # Update the wizard lines with the computed values
        for wizard_line in values_by_lines:
            wizard_line.write(values_by_lines[wizard_line])

    @api.multi
    def action_button_validate(self):
        self.ensure_one()

        # update the interventions with a temporary state to allow the start date update
        current_states = {
            intervention: intervention.state for intervention in self.line_ids.mapped('intervention_id')}
        self.line_ids.mapped('intervention_id').write({'state': 'being_optimized'})

        # build a mapping between tour lines and wizard lines to be able to retrieve them during the process
        wizard_line_mapping = dict(zip(self.line_ids.mapped('tour_line_id'), self.line_ids))

        # get the lines to reorganize
        reorganized_tour_lines = self.env['of.planning.tour.line']
        for line in self.line_ids.sorted(lambda l: l.sequence):
            reorganized_tour_lines |= line.tour_line_id

        # update the wizard lines with the new time slot created by the optimization
        self._update_reorganization_lines_date(reorganized_tour_lines, wizard_line_mapping)

        # update the wizard lines with the new distance, duration and geojson data
        self._update_totals_and_lines_with_osrm_data(reorganized_tour_lines, wizard_line_mapping, update_totals=False)

        # Update the tour lines with the new sequence and the geojson data updated from the optimization
        with self.env.norecompute():
            # we have to start enumerating from 1 to avoid having a sequence of 0 because of the editable O2M field
            for index, line in enumerate(self.line_ids.sorted(lambda l: l.sequence), 1):
                date_before_modification = line.intervention_id.date
                date_deadline_before_modification = line.intervention_id.date_deadline
                forced_date_before_modification = line.intervention_id.date_deadline_forcee
                check_availability_before_modification = line.intervention_id.verif_dispo
                force_date_before_modification = line.intervention_id.forcer_dates
                line.intervention_id.with_context(
                    from_tour_wizard=True
                ).write(self._get_new_values_for_intervention(line))
                tour_line_values = self.tour_id._prepare_tour_line(index, line.intervention_id)
                del tour_line_values['tour_id']
                tour_line_values.update({
                    'last_modification_date': fields.Datetime.now(),
                    'date_before_modification': date_before_modification,
                    'date_deadline_before_modification': date_deadline_before_modification,
                    'forced_date_before_modification': forced_date_before_modification,
                    'check_availability_before_modification': check_availability_before_modification,
                    'force_date_before_modification': force_date_before_modification,
                    'geojson_data': line.geojson_data,
                    'endpoint_geojson_data': line.endpoint_geojson_data,
                    'endpoint_duration': line.endpoint_duration,
                    'endpoint_distance': line.endpoint_distance,
                    'duration_one_way': line.new_duration,
                    'distance_one_way': line.new_distance,
                    'osrm_query': line.osrm_query
                })
                line.tour_line_id.write(tour_line_values)
        self.tour_id.is_optimized = False  # the tour is not optimized by OSRM anymore
        self.tour_id.recompute()
        # update the interventions with their old state
        for intervention, state in current_states.items():
            intervention.write({'state': state})
        return self.action_close_and_reload_tour()

    @api.multi
    def action_open(self, custom_title=None):
        """ Open the wizard view.
        """
        self.ensure_one()
        form_view = self.env.ref('of_planning_tournee.of_tour_planning_reorganization_wizard_view_form')
        title = _("Reorganize tour")
        if custom_title:
            title += ' - ' + custom_title
        return self.action_open_form_view(title, form_view)


class OFTourPlanningReorganizationLineWizard(models.TransientModel):
    _name = 'of.tour.planning.reorganization.line.wizard'
    _inherit = 'of.tour.planning.wizard.line.mixin'

    _description = "Tour Planning Reorganization Wizard Line"

    wizard_id = fields.Many2one(comodel_name='of.tour.planning.reorganization.wizard', string="Wizard")
    old_sequence = fields.Integer(string="Old sequence", readonly=True)
    sequence = fields.Integer(string="Sequence")
    address_city = fields.Char(string="Ville", readonly=True)
    duration_one_way = fields.Float(string="Duration (h)", copy=False)
    distance_one_way = fields.Float(string="Distance (km)", copy=False)
    # Related fields from intervention
    date_start = fields.Datetime(related='intervention_id.date', string="Start date", readonly=True)
    employee_ids = fields.Many2many(related='intervention_id.employee_ids', string="Employees", readonly=True)
    duration = fields.Float(related='intervention_id.duree', string="Duration", readonly=True)
    tache_name = fields.Char(related='intervention_id.tache_id.name', readonly=True)
    partner_name = fields.Char(related='intervention_id.partner_id.name', readonly=True)
    partner_name = fields.Char(related='intervention_id.partner_id.name', readonly=True)
    address_zip = fields.Char(related='intervention_id.address_id.zip', readonly=True)
    partner_phone = fields.Char(related='intervention_id.partner_id.phone', readonly=True)
    partner_mobile = fields.Char(related='intervention_id.partner_id.mobile', readonly=True)
