# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import api, models, fields, _
from odoo.exceptions import UserError
from ..models.of_planning_tour_line import ROUTES_AVAILABLE_COLORS, AVAILABLE_COLORS_TOUR_LINES
from odoo.tools.float_utils import float_compare
from odoo.addons.of_planning_tournee.models.of_planning_tournee import DEFAULT_AM_LIMIT_FLOAT


class OFTourPlanningOptimizationWizard(models.TransientModel):
    _name = 'of.tour.planning.optimization.wizard'
    _inherit = 'of.tour.planning.wizard.mixin'

    _description = "Tour Planning Optimization Wizard"

    state = fields.Selection(selection=[('init', "Init"), ('optimized', "Optimized")], string="State", default='init')
    line_ids = fields.One2many(
        comodel_name='of.tour.planning.optimization.line.wizard', inverse_name='wizard_id', string="Lines to optimize")
    optimized_line_ids = fields.One2many(
        comodel_name='of.tour.planning.optimization.line.wizard', compute='_compute_optimized_line_ids',
        string="Optimized lines")
    map_optimized_line_ids = fields.One2many(
        comodel_name='of.tour.planning.optimization.line.wizard', compute='_compute_optimized_line_ids',
        string="Optimized lines (map)")
    can_overlap_lunchbreak = fields.Boolean(string="Can overlap lunch break ?")
    display_overlap_opt = fields.Boolean(
        string="Display overlap option ?", compute='_compute_display_overlap_opt',
        help="Technical field to display the overlap option in the wizard view when needed")
    display_multi_employees_opt = fields.Boolean(
        string="Display multi employees option ?", compute='_compute_display_multi_employees_opt',
        help="Technical field to display the multi employees option in the wizard view when needed")
    total_distance = fields.Float(related='tour_id.total_distance')
    total_duration = fields.Float(related='tour_id.total_duration')
    new_total_distance = fields.Float(
        string="New total dist. (km)", readonly=True,
        help="The optimized total distance of the tour, that includes the distance from the start address and "
        "to the stop address (km)")
    new_total_duration = fields.Float(
        string="New total dur. (h)", readonly=True,
        help="The optimized total duration of the tour, that includes the duration from the start address and "
        "to the stop address (h)")
    optim_mode = fields.Selection(
        selection=[
            ('all', u"Journée entière"),
            ('half', u"À la demi-journée"),
            ('morning', u"Matin"),
            ('afternoon', u"Après-midi")], string=u"Mode d'optim.", default='all')
    # Related fields
    start_address_id = fields.Many2one(related='tour_id.start_address_id', readonly=True)
    return_address_id = fields.Many2one(related='tour_id.return_address_id', readonly=True)
    additional_records = fields.Text(related='tour_id.additional_records', string="Additionnal records")
    map_tour_line_ids = fields.One2many(related='tour_id.map_tour_line_ids', string="Tour lines")

    @api.multi
    def _compute_optimized_line_ids(self):
        for wizard in self:
            sorted_lines = wizard.line_ids.sorted(key=lambda l: l.new_index)
            wizard.map_optimized_line_ids = sorted_lines
            wizard.optimized_line_ids = sorted_lines

    @api.multi
    def _compute_display_overlap_opt(self):
        """ Compute the display_overlap_opt field to display the overlap option in the wizard view when needed.
        This option is displayed when at least one of the tour lines could overlap the lunch break.
        And it's hidden when the user has already checked the option and relaunch the optimization.
        """
        for wizard in self:
            wizard.display_overlap_opt = any(wizard.map_optimized_line_ids.mapped('could_overlap'))

    @api.multi
    def _compute_display_multi_employees_opt(self):
        """ Compute the display_multi_employees_opt field to display the multi employees option in the wizard view
        when needed.
        This option is displayed when at least one of the tour lines has got multiple employees.
        It will allow the user to choose if he wants to force the new date on interventions with multiple employees.
        """
        for wizard in self:
            tour_lines = wizard.map_optimized_line_ids.mapped('tour_line_id')
            wizard.display_multi_employees_opt = any(
                len(intervention_id.employee_ids) > 1 for intervention_id in tour_lines)

    @api.multi
    def _update_optimization_lines_time_slots(self, optimized_line_order, wizard_line_mapping):
        """ Update the wizard lines with the new values got from the optimized lines.
        """
        self.ensure_one()

        # Get the new values for the wizard lines from the optimized tour lines
        values_by_lines = self._get_new_slot_data_by_lines(
            optimized_line_order, wizard_line_mapping, time_slot_label=True)
        # Update the wizard lines with the computed values
        for wizard_line in values_by_lines:
            wizard_line.write(values_by_lines[wizard_line])

    @api.multi
    def action_button_optimize(self):
        """ Optimize the tour lines.

        :return: the action to open the wizard
        :rtype: dict
        """
        self.ensure_one()
        self.tour_id._test_osrm_connection()
        self.action_optimize()
        self.state = 'optimized'
        return self.action_open(custom_title=self.tour_id.name)

    @api.multi
    def action_button_relaunch(self):
        return self.action_button_optimize()

    @api.multi
    def button_preview_overlap_lb(self):
        """ Preview optimized tour lines with the lunch break overlap option checked.
        This option is used to allow tour lines to overlap the lunch break time slot.
        """
        self.ensure_one()
        self.can_overlap_lunchbreak = True
        return self.action_button_optimize()

    @api.multi
    def button_validate_overlap_lb(self):
        """ Validate optimized tour lines directly after allowing tour lines to overlap the lunch break time slot.
        """
        self.ensure_one()
        self.can_overlap_lunchbreak = True
        return self.action_button_validate()

    @api.model
    def _get_optimized_waypoints(self, tour, mode, afternoon_start_address=False):
        coordinates = tour._get_tour_coordinates_data(mode, afternoon_start_address=afternoon_start_address)

        # send the request to the OSRM server to get the optimized tour lines with the TSP algorithm
        res = tour._send_osrm_trip_request(coordinates_str=';'.join(coord['coord_str'] for coord in coordinates))
        waypoints = res.get('waypoints')
        if not waypoints:
            # we should always get a list of waypoints here
            raise UserError(_("No optimized tour lines found."))
        for index, waypoint in enumerate(waypoints):
            waypoint['origin_line_id'] = coordinates[index]['origin_line_id']
        # sort the waypoints by index to get the optimized tour lines in the right order
        # OSRM will always return the data in the input order, so we need to sort them by index
        waypoints = sorted(waypoints, key=lambda k: k['waypoint_index'])
        return waypoints

    @api.multi
    def action_optimize(self):
        """Optimize the tour lines.
        1 - Get the tour lines coordinates and their hints to be able to retrieve them during the process
        2 - Send the request to the OSRM server to get the optimized tour lines with the TSP algorithm
        3 - Update the wizard lines with the new time slot built from the new optimized trip
        4 - Update the wizard lines with the new distance from the new optimized trip
            > We can't get the new distance from the "trip OSRM API", because the trip service response doesn't return
                the distance between each reordonned waypoints.
            > We have to compute it manually using the "route OSRM API" with the new optimized route.
        """
        self.ensure_one()

        # build a mapping between tour lines and wizard lines to be able to retrieve them during the process
        wizard_line_mapping = dict(zip(self.line_ids.mapped('tour_line_id'), self.line_ids))

        # get the the coordinates of the tour lines to optimize to send them to the OSRM server
        # and also get the tour lines data by hint to be able to retrieve them during the process
        if self.optim_mode != 'half':
            ordered_waypoints = self._get_optimized_waypoints(self.tour_id, self.optim_mode)
        else:
            waypoints_morning = self._get_optimized_waypoints(self.tour_id, 'morning')
            waypoints_morning.pop()

            afternoon_start_address = waypoints_morning[-1]['origin_line_id'].intervention_id.address_id

            waypoints_afternoon = self._get_optimized_waypoints(
                self.tour_id, 'afternoon', afternoon_start_address=afternoon_start_address)
            waypoints_afternoon.pop(0)
            morning_pts_num = len(waypoints_morning)
            for waypoint in waypoints_afternoon:
                waypoint['waypoint_index'] = waypoint['waypoint_index'] + morning_pts_num - 1

            ordered_waypoints = waypoints_morning + waypoints_afternoon

        am_limit_float = self.env['ir.values'].get_default(
            'of.intervention.settings', 'tour_am_limit_float') or DEFAULT_AM_LIMIT_FLOAT
        compare_precision = 5

        optimized_line_order = self.env['of.planning.tour.line']
        if self.optim_mode == 'afternoon':
            optimized_line_order |= self.tour_id.tour_line_ids.filtered(
                lambda tl: float_compare(
                    self.tour_id._get_float_intervention_start_hour(tl.intervention_id),
                    am_limit_float, compare_precision) < 0)

        for waypoint in ordered_waypoints:
            if waypoint['origin_line_id'] != -1:
                optimized_line_order += waypoint['origin_line_id']

        if self.optim_mode == 'morning':
            optimized_line_order |= self.tour_id.tour_line_ids.filtered(
                lambda tl: float_compare(
                    self.tour_id._get_float_intervention_start_hour(tl.intervention_id),
                    am_limit_float, compare_precision) >= 0)

        # update the wizard lines with the new time slot created by the optimization
        self._update_optimization_lines_time_slots(optimized_line_order, wizard_line_mapping)

        # as we have modified the order of the interventions, we need to update the wizard lines with
        # the new distance and duration between each interventions
        self._update_totals_and_lines_with_osrm_data(optimized_line_order, wizard_line_mapping, update_totals=True)

    @api.multi
    def action_button_reset(self):
        """ Reset the wizard to its initial state.

        :return: the action to open the wizard
        :rtype: dict
        """
        self.ensure_one()
        self.line_ids.unlink()
        lines_values = []
        for tour_line in self.tour_id.tour_line_ids:
            line_dict = tour_line._prepare_optimization_line()
            lines_values.append((0, 0, line_dict))
        self.write({
            'state': 'init',
            'line_ids': lines_values,
            'can_overlap_lunchbreak': False
        })
        return self.action_open(custom_title=self.tour_id.name)

    @api.multi
    def action_button_validate(self):
        """ Validate the optimized tour.
        Update all the interventions in the lines with the start date got from the optimization.
        Also updates the interventions sequences in the tour and the tour lines's geojson data.

        As we have modified the interventions order, we need to update the tour lines with the new
        distance, duration and time slot between each interventions.

        :return: the action to open the tour
        :rtype: dict
        """
        self.ensure_one()
        if self.can_overlap_lunchbreak and self.display_overlap_opt:
            # if the user has checked the "can overlap lunchbreak" checkbox and didn't relaunch the optimization,
            # we need to relaunch the optimization to take into account the new lunchbreaks
            self.action_optimize()

        # update the interventions with a temporary state to allow the start date update
        current_states = {
            intervention: intervention.state for intervention in self.line_ids.mapped('intervention_id')}
        self.line_ids.mapped('intervention_id').with_context(from_tour_wizard=True).write({'state': 'being_optimized'})
        with self.env.norecompute():  # disable recomputing the fields during the update
            for line in self.line_ids:
                date_before_modification = line.intervention_id.date
                date_deadline_before_modification = line.intervention_id.date_deadline
                forced_date_before_modification = line.intervention_id.date_deadline_forcee
                check_availability_before_modification = line.intervention_id.verif_dispo
                force_date_before_modification = line.intervention_id.forcer_dates
                # update the interventions with the new start date
                line.intervention_id.with_context(
                    from_tour_wizard=True
                ).write(self._get_new_values_for_intervention(line))
                # update the line with the new sequence and the geojson data updated from the optimization
                tour_line_values = self.tour_id._prepare_tour_line(line.new_index, line.intervention_id)
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
        # update helper fields
        self.tour_id.write({
            'is_optimized': True,
            'ignore_alert_optimization_update': False
        })
        self.tour_id.recompute()
        # update the interventions to bring them back to their old states
        for intervention, state in current_states.items():
            intervention.with_context(from_tour_wizard=True).write({'state': state})
        return self.action_close_and_reload_tour()

    @api.multi
    def action_open(self, custom_title=None):
        """ Open the wizard view.

        :param custom_title: the custom title to add to the wizard title
        :return: the action to open the wizard
        :rtype: dict
        """
        self.ensure_one()
        form_view = self.env.ref('of_planning_tournee.of_tour_planning_optimization_wizard_view_form')
        title = _("Optimize tour")
        if custom_title:
            title += " - " + custom_title
        return self.action_open_form_view(title, form_view)


class OFTourPlanningOptimizationLineWizard(models.TransientModel):
    _name = 'of.tour.planning.optimization.line.wizard'
    _inherit = 'of.tour.planning.wizard.line.mixin'

    _description = "Tour Planning Optimization Wizard Line"

    wizard_id = fields.Many2one(comodel_name='of.tour.planning.optimization.wizard', string="Wizard")
    wizard_state = fields.Selection(string="State", related='wizard_id.state')
    new_intervention_id = fields.Many2one(
        comodel_name='of.planning.intervention', string="New Intervention",
        help="Technical field used by the map of the optimized tour lines to display data on the map")
    flexible = fields.Boolean(string="Flexible", related='intervention_id.flexible')
    workers_names = fields.Char(string="Workers", compute='_compute_workers_names')
    old_index = fields.Integer(string="Old index")
    old_time_slot = fields.Char(string="Old Time Slot")
    new_index = fields.Integer(string="New index")
    new_time_slot = fields.Char(string="New Time Slot")
    old_duration = fields.Float(string="Duration (h)")
    old_distance = fields.Float(string="Distance (km)")
    # Map fields
    geo_lat = fields.Float(related='new_intervention_id.geo_lat', string="Latitude", readonly=True)
    geo_lng = fields.Float(related='new_intervention_id.geo_lng', string="Longitude", readonly=True)
    employee_ids = fields.Many2many(related='new_intervention_id.employee_ids', string="Employees", readonly=True)
    duration = fields.Float(related='new_intervention_id.duree', string="Duration", readonly=True)
    tache_name = fields.Char(related='new_intervention_id.tache_id.name', readonly=True)
    partner_name = fields.Char(related='new_intervention_id.partner_id.name', readonly=True)
    address_zip = fields.Char(related='new_intervention_id.address_id.zip', readonly=True)
    address_city = fields.Char(related='new_intervention_id.address_city', readonly=True)
    partner_phone = fields.Char(related='new_intervention_id.partner_id.phone', readonly=True)
    partner_mobile = fields.Char(related='new_intervention_id.partner_id.mobile', readonly=True)
    map_color_tour = fields.Char(related='new_intervention_id.map_color_tour', string="Color")
    tour_number = fields.Integer(related='new_index', string="Tour number", readonly=True)
    hexa_color = fields.Char(string="Hexa color", compute='_compute_hexa_color')

    @api.multi
    @api.depends('intervention_id')
    def _compute_workers_names(self):
        for line in self:
            line.workers_names = ', '.join(line.intervention_id.employee_ids.mapped('name')) \
                if line.intervention_id and line.intervention_id.employee_ids else False

    @api.multi
    @api.depends('intervention_id')
    def _compute_hexa_color(self):
        tours = self.mapped('wizard_id.tour_id')
        color_padding_by_tour = {
            tour: max(len(ROUTES_AVAILABLE_COLORS) / len(tour.tour_line_ids), 1) for tour in tours}
        last_index = 0
        for line in self.sorted(key=lambda l: l.new_index):
            color_padding = color_padding_by_tour[line.wizard_id.tour_id]
            sequence = line.new_index - 1 if line.new_index > 0 else 0
            color_index = last_index + color_padding if sequence > 0 else last_index
            last_index = color_index
            line.hexa_color = AVAILABLE_COLORS_TOUR_LINES[min(color_index, len(AVAILABLE_COLORS_TOUR_LINES)-1)]

    @api.model
    def custom_get_color_map(self):
        return self.tour_line_id.custom_get_color_map()
