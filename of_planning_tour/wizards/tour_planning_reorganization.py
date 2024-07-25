# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import _, fields, models


class OFTourPlanningReorganizationWizard(models.TransientModel):
    """Tour Planning Reorganization Wizard"""

    _name = 'of.planning.tour.reorganization.wizard'
    _description = __doc__
    _inherit = 'of.planning.tour.wizard.mixin'

    line_ids = fields.One2many(
        comodel_name='of.planning.tour.reorganization.line.wizard',
        inverse_name='wizard_id',
        string="Lines to reorganize",
    )

    def _update_reorganization_lines_date(self, reorganized_tour_lines, wizard_line_mapping):
        """Update the wizard lines with the new time slot created by the optimization"""
        self.ensure_one()

        # Get the new values for the wizard lines from the optimized tour lines
        values_by_lines = self._get_new_slots_data_by_lines(
            reorganized_tour_lines, wizard_line_mapping, time_slot_label=False
        )
        # Update the wizard lines with the computed values
        for wizard_line in values_by_lines:
            values = values_by_lines[wizard_line]
            values = {key: values[key] for key in values if key in wizard_line._fields}
            wizard_line.write(values)

    def action_button_validate(self):
        """
        Perform the validation and reorganization of tour planning.

        This method updates the interventions, wizard lines, tour lines, and tour optimization status
        based on the reorganization process.

        Returns:
            The result of the action_close_and_reload_tour method.
        """
        self.ensure_one()

        # update the interventions with a temporary state to allow the start date update
        current_events_states = {event: event.of_state for event in self.mapped('line_ids.intervention_id')}
        self.mapped('line_ids.intervention_id').write({'of_state': 'being_optimized'})

        # build a mapping between tour lines and wizard lines to be able to retrieve them during the process
        wizard_line_mapping = dict(zip(self.mapped('line_ids.tour_line_id'), self.line_ids))

        # get the lines to reorganize
        reorganized_tour_lines = self.env['of.planning.tour.line']
        for line in self.line_ids.sorted('sequence'):
            reorganized_tour_lines |= line.tour_line_id

        # update the wizard lines with the new time slot created by the optimization
        self._update_reorganization_lines_date(reorganized_tour_lines, wizard_line_mapping)

        # update the wizard lines with the new distance, duration and geojson data
        self._update_totals_and_lines_with_osrm_data(reorganized_tour_lines, wizard_line_mapping, update_totals=False)

        # Update the tour lines with the new sequence and the geojson data updated from the optimization
        with self.env.norecompute():
            # we have to start enumerating from 1 to avoid having a sequence of 0 because of the editable O2M field
            for index, line in enumerate(self.line_ids.sorted('sequence'), 1):
                date_before_modification = line.intervention_id.start
                date_deadline_before_modification = line.intervention_id.stop
                force_date_before_modification = line.intervention_id.of_force_dates
                line.intervention_id.with_context(of_avoid_tour_process=True).write(
                    self._get_new_values_for_intervention(line)
                )
                tour_line_values = self.tour_id._prepare_tour_line_values(index, line.intervention_id)
                del tour_line_values['tour_id']
                tour_line_values.update(
                    {
                        'last_modification_date': fields.Datetime.now(),
                        'date_before_modification': date_before_modification,
                        'date_deadline_before_modification': date_deadline_before_modification,
                        'force_date_before_modification': force_date_before_modification,
                        'geometry_data': line.geometry_data,
                        'endpoint_geometry_data': line.endpoint_geometry_data,
                        'endpoint_duration': line.endpoint_duration,
                        'endpoint_distance': line.endpoint_distance,
                        'duration_one_way': line.new_duration,
                        'distance_one_way': line.new_distance,
                        'osrm_query': line.osrm_query,
                    }
                )
                line.tour_line_id.write(tour_line_values)

        # tour is not considered as optimized anymore
        self.tour_id.is_optimized = False

        self.tour_id.flush_recordset()

        # update the interventions with their old state
        for event, state in current_events_states.items():
            event.write({'of_state': state})
        return self.action_close_and_reload_tour()

    def action_button_open(self, custom_title=None):
        """Open the wizard view."""
        self.ensure_one()
        form_view = self.env.ref('of_planning_tour.of_tour_planning_reorganization_wizard_view_form')
        title = _("Reorganize tour")
        if custom_title:
            title += f' - {custom_title}'
        return self.action_open_form_view(title, form_view)


class OFTourPlanningReorganizationLineWizard(models.TransientModel):
    """Tour Planning Reorganization Wizard Line"""

    _name = 'of.planning.tour.reorganization.line.wizard'
    _inherit = 'of.planning.tour.wizard.line.mixin'

    _description = __doc__

    wizard_id = fields.Many2one(comodel_name='of.planning.tour.reorganization.wizard', string="Wizard")
    old_sequence = fields.Integer(readonly=True)
    sequence = fields.Integer()
    address_city = fields.Char(string="City", readonly=True)
    duration_one_way = fields.Float(string="Duration (h)", copy=False)
    distance_one_way = fields.Float(string="Distance (km)", copy=False)
    # Related fields from intervention
    date_start = fields.Datetime(related='intervention_id.start', string="Start date", readonly=True)
    employee_ids = fields.Many2many(related='intervention_id.of_employee_ids', string="Employees", readonly=True)
    duration = fields.Float(related='intervention_id.duration', string="Duration", readonly=True)
    task_name = fields.Char(related='intervention_id.of_task_id.name', readonly=True, string="Task")
    partner_name = fields.Char(related='intervention_id.of_partner_id.name', readonly=True, string="Partner")
    address_zip = fields.Char(related='intervention_id.of_address_id.zip', readonly=True)
    partner_phone = fields.Char(related='intervention_id.of_partner_id.phone', readonly=True)
    partner_mobile = fields.Char(related='intervention_id.of_partner_id.mobile', readonly=True)
