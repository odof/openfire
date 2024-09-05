# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import ast
import json
import logging
from datetime import datetime, time, timedelta
from urllib.parse import urlparse

import pytz
import requests

from odoo import Command, _, api, fields, models
from odoo.exceptions import UserError
from odoo.tools import config

_logger = logging.getLogger(__name__)

TZ_EUROPE_PARIS = 'Europe/Paris'

AM_LIMIT_FLOAT = 12.0  # Define the limit between AM and PM
DEFAULT_MIN_DURATION_IN_HOURS = 0.5  # Default minimum duration between two interventions in hours
DEFAULT_PERIOD_IN_DAYS = 30
SECURITY_MARGIN_IN_DAYS = 10  # Security margin in minutes to add to the duration of the interventions

# Mapping dictionary to translate the weekday name to the short version
WEEKDAYS_STR_TR = {
    'Monday': 'mon',
    'Tuesday': 'tue',
    'Wednesday': 'wed',
    'Thursday': 'thu',
    'Friday': 'fri',
    'Saturday': 'sat',
    'Sunday': 'sun',
    # also add french keys to avoid error on servers with french language (s-hotel)
    'Lundi': 'mon',
    'Mardi': 'tue',
    'Mercredi': 'wed',
    'Jeudi': 'thu',
    'Vendredi': 'fri',
    'Samedi': 'sat',
    'Dimanche': 'sun',
}
OPENFIRE_LAT = '48.152344'
OPENFIRE_LNG = '-1.7008439'

DEFAULT_TIMEOUT = 10  # Default timeout for requests to the OSRM server


class OFPlanningTour(models.Model):
    """Tour"""

    _name = 'of.planning.tour'
    _inherit = ['of.readgroup', 'mail.thread']
    _description = __doc__
    _order = 'date DESC'

    name = fields.Char(compute='_compute_tour_name', store=True)
    state = fields.Selection(
        selection=[('1-draft', "Draft"), ('2-full', "Full"), ('3-confirmed', "Confirmed")],
        index=True,
        readonly=True,
        default='1-draft',
        tracking=True,
        copy=False,
        help=" * 'Draft' : With remaining available slots, unconfirmed.\n"
        " * 'Full' : No slots available.\n"
        " * 'Confirmed' : Click on “Confirm” (may or may not have slots available)",
    )

    # Dates and weekdays
    date = fields.Date(required=True, default=fields.Date.today())
    date_min = fields.Date(related='date', string="Date min", help="Technical field used to filter the tours")
    date_max = fields.Date(related='date', string="Date max", help="Technical field used to filter the tours")
    weekday = fields.Selection(
        selection=[
            ('mon', "Monday"),
            ('tue', "Tuesday"),
            ('wed', "Wednesday"),
            ('thu', "Thursday"),
            ('fri', "Friday"),
            ('sat', "Saturday"),
            ('sun', "Sunday"),
        ],
        compute='_compute_date_weekday',
        store=True,
    )
    week_type = fields.Selection(
        selection=[('1', 'Second'), ('0', 'First')], string='Week Number', compute='_compute_week_type', store=True
    )

    # Employee
    employee_id = fields.Many2one(comodel_name='hr.employee', string="Operators", required=True, ondelete='cascade')
    employee_other_ids = fields.Many2many(
        comodel_name='hr.employee',
        relation='tour_employee_other_rel',
        column1='tour_id',
        column2='employee_id',
        string="Team members",
        domain="['|', ('of_is_operator', '=', True), ('of_is_salesperson', '=', True)]",
        copy=False,
    )

    # Address data
    start_address_id = fields.Many2one(
        comodel_name='res.partner',
        string="Start address",
        help="Start address of the tour",
        compute='_compute_address_data',
        store=True,
        readonly=False,
    )
    return_address_id = fields.Many2one(
        comodel_name='res.partner',
        string="Return address",
        help="Return address of the tour",
        compute='_compute_address_data',
        store=True,
        readonly=False,
    )

    # Sectors
    sector_ids = fields.Many2many(
        comodel_name='of.sector',
        relation='tour_sector_rel',
        column1='tour_id',
        column2='sector_id',
        string="Sectors",
        domain="[('type', 'in', ['technical', 'technical_commercial'])]",
        copy=False,
    )
    sector_kanban_names = fields.Text(string="Sector names", compute='_compute_sector_kanban_names')

    # Distance and duration
    total_distance = fields.Float(
        string="Total distance (km)",
        readonly=True,
        compute='_compute_total_distance_and_duration',
        store=True,
        help="Total distance of the tour, that includes the distance to go from the start address and to the stop"
        " address (km)",
        copy=False,
    )
    total_duration = fields.Float(
        string="Total duration (h)",
        readonly=True,
        compute='_compute_total_distance_and_duration',
        store=True,
        help="Total duration of the tour, that includes the distance to go from the start address and to the stop"
        " address (h)",
        copy=False,
    )

    # Interventions, lines and available slots
    intervention_ids = fields.Many2many(
        comodel_name='calendar.event',
        relation='calendar_event_of_planning_tour_rel',
        column1='tour_id',
        column2='event_id',
        string="Interventions",
        copy=False,
    )
    intervention_count = fields.Integer(string="# Interventions", compute='_compute_count_interventions', store=True)
    tour_line_ids = fields.One2many(
        comodel_name='of.planning.tour.line', inverse_name='tour_id', string="Tour lines", copy=False
    )
    available_slot_ids = fields.One2many(
        comodel_name='of.planning.available.slot', inverse_name='tour_id', string="Available Slots", copy=False
    )
    max_line_sequence = fields.Integer(string="Max sequence in lines", compute='_compute_max_line_sequence', store=True)

    # Helpers
    is_full = fields.Boolean(compute='_compute_is_full', string="Full", store=True)
    is_optimized = fields.Boolean(string="Optimized", help="Is the tour is optimized by the OSRM server ?")
    last_modification_date = fields.Datetime(
        string="Last modification date",
        compute='_compute_last_modification_date',
        help="Technical field used to store the max date of the last modification of the tour lines",
        store=True,
    )
    need_optimization_update = fields.Boolean(
        string="Need new optimization",
        compute='_compute_need_new_optimization',
        help="Technical field used to alert Users that geodata have changed since the last optimization."
        "If True, the tour needs to be optimized again",
        store=True,
    )
    ignore_alert_optimization_update = fields.Boolean(string="Ignore alert for optimization update")
    hide_action_buttons = fields.Boolean(
        string="Hide action buttons",
        compute='_compute_hide_action_buttons',
        help="Technical field used to hide the wizard actions buttons",
    )

    # Map and OSRM routes fields
    additional_records = fields.Text(compute='_compute_additional_records')
    map_tour_line_ids = fields.One2many(
        comodel_name='of.planning.tour.line', compute='_compute_map_tour_line_ids', string="Tour lines (map)"
    )
    map_latitude = fields.Text(
        string="Latitude (map)",
        help="Technical field user to center the map on the tour",
        compute='_compute_map_tour_line_ids',
    )
    map_longitude = fields.Text(
        string="Longitude (map)",
        help="Technical field user to center the map on the tour",
        compute='_compute_map_tour_line_ids',
    )
    map_tour_line_coordinates = fields.Char(string="Tour Coordinates", compute='_compute_map_tour_line_coordinates')

    # Search fields
    gb_sector_id = fields.Many2one(
        comodel_name='of.sector',
        compute=lambda *a, **k: {},
        search='_search_gb_sector_id',
        string="Sector",
        of_custom_groupby=True,
    )

    _sql_constraints = [
        (
            'date_employee_uniq',
            'unique (date, employee_id)',
            "A tour already exists for this employee on this date.",
        )
    ]

    # ---------------------------------------------------------
    # Compute methods
    # ---------------------------------------------------------

    @api.depends('date', 'employee_id')
    def _compute_tour_name(self):
        for record in self:
            date_str = False
            if record.date:
                date_str = record.date.strftime('%d/%m/%Y')
            record.name = f"{record.employee_id.name}{f' - {date_str}' or ''}"

    @api.depends('date')
    def _compute_date_weekday(self):
        if not self.env.context.get('tz'):
            self = self.with_context(tz=TZ_EUROPE_PARIS)
        for tour in self:
            day_value = False
            if tour.date:
                tour_date_dt = fields.Datetime.to_datetime(tour.date)
                local_date = fields.Datetime.context_timestamp(self, tour_date_dt)
                day_value = WEEKDAYS_STR_TR[local_date.strftime('%A').capitalize()]
            tour.weekday = day_value

    @api.depends('date')
    def _compute_week_type(self):
        attendance_obj = self.env['resource.calendar.attendance']
        for tour in self:
            tour.week_type = str(attendance_obj.get_week_type(tour.date))

    @api.depends('employee_id')
    def _compute_address_data(self):
        for tour in self:
            if tour.employee_id:
                tour.start_address_id = tour.employee_id.of_start_address_id.id
                tour.return_address_id = tour.employee_id.of_return_address_id.id

    def _compute_additional_records(self):
        """Compute the additional records field that contains the data of the start and stop markers of the tour."""
        for tour in self:
            start_marker, end_marker = tour._get_start_stop_markers_data_for_tour()
            tour.additional_records = json.dumps([start_marker, end_marker])

    @api.depends('tour_line_ids')
    def _compute_count_interventions(self):
        for tour in self:
            tour.intervention_count = len(tour.mapped('tour_line_ids.intervention_id'))

    @api.depends('tour_line_ids.geodata_update_date', 'last_modification_date', 'ignore_alert_optimization_update')
    def _compute_need_new_optimization(self):
        for tour in self:
            max_date = max(tour.mapped('tour_line_ids.geodata_update_date')) if tour.tour_line_ids else False
            tour.need_optimization_update = (
                max_date > tour.last_modification_date
                if tour.date >= fields.Date.today()  # we don't need to optimize past tours
                and max_date
                and tour.last_modification_date
                and not tour.ignore_alert_optimization_update
                else False
            )

    @api.depends('tour_line_ids', 'tour_line_ids.sequence')
    def _compute_map_tour_line_ids(self):
        for tour in self:
            tour.map_tour_line_ids = tour.tour_line_ids.sorted('sequence')
            tour.map_latitude, tour.map_longitude = tour._get_center_map_coordinates()

    @api.depends('map_tour_line_ids')
    def _compute_map_tour_line_coordinates(self):
        """Prepare the coordinates of the tour for the OSRM"""
        for tour in self:
            origin = tour.start_address_id
            arrival = tour.return_address_id

            tour_lines = [f"{round(origin.partner_longitude, 7)},{round(origin.partner_latitude, 7)}"]  # noqa
            tour_lines.extend(
                f"{round(line.geo_lng, 7)},{round(line.geo_lat, 7)}"  # noqa
                for line in tour.map_tour_line_ids.filtered(lambda tl: tl.geo_lng and tl.geo_lat)
            )
            tour_lines.append(f"{round(arrival.partner_longitude, 7)},{round(arrival.partner_latitude, 7)}")  # noqa

            tour.map_tour_line_coordinates = ';'.join(tour_lines)

    def _compute_hide_action_buttons(self):
        """Hide wizard action buttons (Optimization/Reorganization) if it has no lines or if it is in the past."""
        for tour in self:
            tour.hide_action_buttons = not tour.tour_line_ids or tour.date < fields.Date.today()

    @api.depends(
        'tour_line_ids.duration_one_way',
        'tour_line_ids.distance_one_way',
        'tour_line_ids.endpoint_distance',
        'tour_line_ids.endpoint_duration',
        'tour_line_ids.is_last_line_of_tour',
    )
    def _compute_total_distance_and_duration(self):
        for tour in self:
            total_distance = total_duration = 0
            for line in tour.tour_line_ids:
                total_distance += line.distance_one_way
                total_duration += line.duration_one_way
                if line.is_last_line_of_tour:
                    total_distance += line.endpoint_distance
                    total_duration += line.endpoint_duration
            tour.total_distance = total_distance
            tour.total_duration = total_duration

    @api.depends('tour_line_ids.last_modification_date')
    def _compute_last_modification_date(self):
        """Get the last modification date of the tour lines."""
        for tour in self:
            tour.last_modification_date = max(
                (d for d in tour.mapped('tour_line_ids.last_modification_date') if d), default=False
            )

    @api.depends(
        'employee_id',
        'date',
        'employee_id.tz',
        'tour_line_ids',
        'tour_line_ids.intervention_id',
    )
    def _compute_is_full(self):
        """A tour full is a tour that is in the past or that has no more available slots."""
        if not self.env.context.get('tz'):
            self = self.with_context(tz=TZ_EUROPE_PARIS)

        event_obj = self.env['calendar.event']
        today = fields.Date.today()
        for tour in self:
            if tour.date < today:
                tour.is_full = True
                continue

            employee = tour.employee_id
            if employee.tz and employee.tz != TZ_EUROPE_PARIS:
                self = self.with_context(tz=employee.tz)

            interventions = event_obj.search(
                [
                    ('of_type', '=', 'intervention'),
                    ('of_employee_ids', 'in', tour.employee_id.id),
                    ('start_date', '<=', tour.date),
                    ('stop_date', '>=', tour.date),
                    ('of_state', 'in', ('draft', 'confirmed')),
                ],
                order='start',
            )
            if not interventions or not tour.tour_line_ids:
                tour.is_full = False
                continue

            employee_wh = employee._get_employee_working_hours_list(tour.date)[employee.id]
            nb_timeslots = len(employee_wh)
            if nb_timeslots == 0:  # employee is not working, so the tour is full
                tour.is_full = True
                continue

            # build the timeline for occupied timeslots of the day for the employee and check if it is full
            min_duration = float(
                self.env['ir.config_parameter'].sudo().get_param('of.planning.tour.available_slot_min_duration_hours')
                or DEFAULT_MIN_DURATION_IN_HOURS
            )
            day_timeline = self._get_employee_day_unavailability_timeline(tour.date, interventions, employee_wh)
            is_full = True
            last_end = 0
            for start, end in day_timeline:
                if start - last_end > min_duration:
                    # there is a gap in the timeline so the tour is not full
                    # we consider that a gap of more than 30 min is enough to consider the tour as not full
                    is_full = False
                    break
                if end > last_end:
                    last_end = end
            tour.is_full = is_full

    @api.depends('tour_line_ids', 'tour_line_ids.sequence')
    def _compute_max_line_sequence(self):
        for tour in self:
            lines = tour.mapped('tour_line_ids.sequence')
            tour.max_line_sequence = lines and max(lines) or 0

    @api.depends('sector_ids')
    def _compute_sector_kanban_names(self):
        for tour in self:
            tour.sector_kanban_names = " - ".join([sector.name for sector in tour.sector_ids])

    def _search_gb_sector_id(self, operator, value):
        return [('sector_ids', operator, value)]

    # ---------------------------------------------------------
    # ORM methods
    # ---------------------------------------------------------

    def _valid_field_parameter(self, field, name):
        # EXTENDS models
        return name == 'of_custom_groupby' or super()._valid_field_parameter(field, name)

    def copy(self, default=None):
        default = dict(default or {}, date=fields.Date.today())
        return super().copy(default)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            vals |= self._process_address_values(vals)
        return super().create(vals_list)

    def write(self, vals):
        if ('start_address_id' in vals and not vals['start_address_id']) or (
            'return_address_id' in vals and not vals['return_address_id']
        ):
            # avoid setting the start or return address to False
            for k in ['start_address_id', 'return_address_id']:
                if k in vals:
                    del vals[k]

        result = super().write(vals)
        if self.env.context.get('reset_sequence'):
            self._reset_sequence()
        return result

    def _write(self, values):
        """Low level implementation of the write method to ensure that we will update the tour state after computing
        fields."""
        saved_values = {
            tour.id: {'start_address_id': tour.start_address_id, 'return_address_id': tour.return_address_id}
            for tour in self
        }

        super()._write(values)

        self._write_update_states(values)
        self._write_recompute_osrm_data(values, saved_values)
        return

    @api.model
    def _read_group_process_groupby(self, gb, query):
        # Ajout de la possibilité de regrouper par employé
        if gb != 'gb_sector_id':
            return super()._read_group_process_groupby(gb, query)

        alias = query.left_join(self._table, 'id', 'tour_sector_rel', 'tour_id', 'sector_ids')

        return {
            'field': gb,
            'groupby': gb,
            'type': 'many2one',
            'display_format': None,
            'interval': None,
            'tz_convert': False,
            'qualified_field': f'"{alias}".sector_id',
        }

    # ---------------------------------------------------------
    # Action methods
    # ---------------------------------------------------------

    def action_button_view_interventions(self):
        """
        Returns an action to view the interventions associated with the tour (linked to tour lines).
        """
        return {
            'name': _("Interventions"),
            'type': 'ir.actions.act_window',
            'res_model': 'calendar.event',
            'view_mode': 'tree,form',
            'domain': [('id', 'in', self.mapped('tour_line_ids.intervention_id').ids)],
        }

    def action_button_confirm_tour(self):
        """Confirm the tour."""
        self.ensure_one()
        self.write({'state': '3-confirmed'})

    def action_button_set_back_draft(self):
        """Set the tour as draft."""
        self.ensure_one()
        self.write({'state': '1-draft'})

    def action_button_set_back_full(self):
        """Set the tour as full."""
        self.ensure_one()
        self.write({'state': '2-full'})

    def action_button_ignore_alert_optimization_update(self):
        """Ignore the alert about tour optimization until the next tour modification."""
        self.ensure_one()
        self.write({'ignore_alert_optimization_update': True})

    def action_button_update_map_and_reload(self):
        """Update the osrm data for the tour and reload the page."""
        self.ensure_one()
        self.action_compute_osrm_data()
        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }

    def action_compute_osrm_data(self, reload=False):
        """
        Compute the OSRM data for each tour line in the current tour.

        Args:
            reload (bool, optional): If True, reload the line data from intervention before computing.
                Defaults to False.
        """
        for tour in self:
            if not tour.tour_line_ids:
                tour._populate_tour_lines()
            for line in tour.tour_line_ids:
                if reload:
                    line._update_line_data_from_intervention()
                # force the recomputation of the line data (previous/next geo_lat, geo_lng etc.)
                line._compute_line_data()
                line._osrm_update_line_data()
        self._fields['map_tour_line_ids'].compute_value(self)

    def action_button_restore_tour(self):
        """
        Restore the tour to its previous state before the last optimization.
        """
        self.ensure_one()

        # save the current state of the interventions to restore it after the tour restoration
        current_states = {
            intervention: intervention.of_state for intervention in self.mapped('tour_line_ids.intervention_id')
        }
        self.mapped('tour_line_ids.intervention_id').with_context(of_avoid_tour_process=True).write(
            {'of_state': 'being_optimized'}
        )

        # restore last saved values
        for line in self.tour_line_ids:
            line.action_restore_intervention_date()

        self.tour_line_ids.write({'last_modification_date': False})

        # restore the state of the interventions
        for intervention, state in current_states.items():
            intervention.with_context(of_avoid_tour_process=True).write({'of_state': state})

        # reset sequence of lines and then recompute the OSRM data
        self._reset_sequence()
        self.with_context(of_force_restore=True).action_compute_osrm_data()

    def action_button_optimize_tour(self):
        """
        Open the wizard to optimize the tour.
        """
        optimization_wizard = self._handle_wizard_opening(
            wizard_model='of.planning.tour.optimization.wizard',
            error_message=_("You must set the start and return addresses before optimizing the tour."),
        )
        return optimization_wizard.action_button_open(custom_title=self.name)

    def action_reorganize_tour(self):
        """Open the wizard to reorganize the tour.

        :return: the action to open the wizard
        """
        reorganization_wizard = self._handle_wizard_opening(
            wizard_model='of.planning.tour.reorganization.wizard',
            error_message=_("You must set the start and return addresses before reorganizing the tour."),
        )

        return reorganization_wizard.action_button_open(custom_title=self.name)

    @api.model
    def action_generate_tour(self, date=False, employee=False):
        """
        Generate a tour for a given date and employee.

        Args:
            date (date): The date for which the tour is generated.
            employee (recorset): The employee for whom the tour is generated.

        Returns:
            tour (object): The generated tour object.

        Raises:
            None
        """
        if not date or not employee:
            return False
        self_sudo = self.sudo()  # to avoid access rights issues if this method is not called from a cron

        tour = self_sudo.search([('date', '=', date), ('employee_id', '=', employee.id)], limit=1)
        if tour:
            return tour

        tour = self_sudo.create(
            {
                'employee_id': employee.id,
                'date': date,
            }
        )
        if tour.intervention_ids and not tour.tour_line_ids:
            # interventions were already existing before tour creation, we need to populate the tour lines
            tour._populate_tour_lines()
        return tour

    def action_update_lines_data(self):
        """
        Update the lines data for the tour.

        This method populates the tour lines and recomputes the data using OSRM if needed.
        """
        for tour in self.sudo():
            tour._populate_tour_lines()
            tour._osrm_recompute_data_if_needed(force=True)

    def action_mass_tour_route_update(self):
        return {
            'name': _("Mass route update"),
            'res_model': 'of.planning.tour.mass.route.update.wizard',
            'view_mode': 'form',
            'context': {
                'active_id': self.ids[0],
                'active_ids': self.ids,
            },
            'target': 'new',
            'type': 'ir.actions.act_window',
        }

    def action_mass_sector_assignation(self):
        return {
            'name': _("Mass sector assignation"),
            'res_model': 'of.planning.tour.mass.sector.assignation.wizard',
            'view_mode': 'form',
            'context': {
                'active_id': self.ids[0],
                'active_ids': self.ids,
            },
            'target': 'new',
            'type': 'ir.actions.act_window',
        }

    # ---------------------------------------------------------
    # Business methods, splitted by topics :
    #  - general
    #  - address
    #  - timeline/availability/working hours
    #  - available time slots
    #  - osrm
    #  - map data related
    # ---------------------------------------------------------

    def _prepare_tour_line_values(self, idx, intervention):
        """
        Prepare the values for a tour line based on the given index and intervention.

        Args:
            idx (int): The sequence index of the tour line.
            intervention (recordset): The intervention record to create the tour line for.

        Returns:
            dict: A dictionary containing the prepared values for the tour line.

        """
        self.ensure_one()
        intervention = intervention.with_context(of_active_tour_id=self.id)
        geo_lat = intervention.of_partner_latitude
        geo_lng = intervention.of_partner_longitude
        address_city = intervention.of_address_city
        return {
            'sequence': idx,
            'tour_id': self.id,
            'intervention_id': intervention.id,
            'geo_lat': geo_lat,
            'geo_lng': geo_lng,
            'address_city': address_city,
            'geodata_update_date': fields.Datetime.now(),
            'duration_one_way': False,
            'distance_one_way': False,
        }

    def _reorder_tour_lines(self):
        """
        Reorders the tour lines based on the start time of the intervention associated with each line.
        Also resets the sequence of the tour lines after reordering.
        """
        for tour in self:
            tour.tour_line_ids = tour.tour_line_ids.sorted(key=lambda line: line.intervention_id.start)
            tour._reset_sequence()

    def _reset_sequence(self):
        """Reset the tour lines sequence depending on each line date_start."""
        for tour in self:
            for current_sequence, line in enumerate(tour.tour_line_ids.sorted('date_start'), start=1):
                line.sequence = current_sequence

    def _set_tours_to_draft(self):
        """
        Sets the tours to 'draft' state if they are not full and their current state is '2-full'.

        This method filters the tours based on the conditions mentioned above and updates their state to '1-draft'
        using the `write` method.
        """
        tours = self.filtered(lambda t: not t.is_full and t.state == '2-full')
        tours and tours.write({'state': '1-draft'})

    def _set_tours_to_full(self):
        """
        Sets the tours to 'full' state if they are full and their current state is '1-draft' and have tour lines.

        This method filters the tours based on the conditions mentioned above and updates their state to '2-full'
        using the `write` method.
        """
        tours = self.filtered(lambda t: t.is_full and t.tour_line_ids and t.state == '1-draft')
        tours and tours.write({'state': '2-full'})

    def _delete_tour_lines(self):
        """Delete all the tour lines of the tour."""
        for tour in self:
            tour.tour_line_ids.unlink()
            tour._reset_sequence()

    def _populate_tour_lines(self):
        """
        Populates the tour lines with interventions that are not already in the tour, if needed.

        This method checks if there are interventions that need to be added to the tour based on certain conditions,
        such as the tour date and the 'of_tour_force_restore' flag in the context. If interventions need to be added,
        it creates new tour lines for each intervention and adds them to the tour.

        Parameters:
            self (RecordSet): The current tour recordset.

        Returns:
            None
        """
        for tour in self:
            # Get the interventions that are not already in the tour to add them if needed
            if (
                (interventions := tour._get_interventions_to_add())
                and tour.date >= fields.Date.today()
                or self.env.context.get('of_tour_force_restore')
            ):
                index = tour.max_line_sequence + 1 if tour.tour_line_ids else 1
                if lines := [
                    Command.create(tour._prepare_tour_line_values(idx, intervention))
                    for idx, intervention in enumerate(interventions, index)
                ]:
                    tour.write({'tour_line_ids': lines})
                    tour._reorganize_available_slot()
                    tour._reset_sequence()

    def _get_interventions_to_add(self):
        """Get the interventions that are not already in the tour to add them if needed."""
        self.ensure_one()
        interventions = self.env['calendar.event'].search(
            [
                ('of_type', '=', 'intervention'),
                ('of_employee_ids', 'in', [self.employee_id.id]),
                ('start_date', '<=', self.date),
                ('stop_date', '>=', self.date),
                ('of_state', 'in', ('draft', 'confirmed', 'ongoing')),
            ],
            order='start',
        )
        return interventions - self.tour_line_ids.mapped('intervention_id')

    def _write_update_states(self, values):
        """
        Updates the states of tours based on the given values after computing fields.
        Called through the `_write` method.

        Args:
            values (dict): The updated values for the planning tour.

        Returns:
            None
        """
        if any(field in values for field in ('is_full', 'state')):
            self._set_tours_to_draft()
            self._set_tours_to_full()

    def _write_recompute_osrm_data(self, values, saved_values):
        """
        Recomputes the OSRM data for the planning tours if the start or return address has changed.
        Called through the `_write` method.

        Args:
            values (dict): The updated values for the planning tour.
            saved_values (dict): The saved values of the planning tour before the update.

        Returns:
            None
        """
        if any(field in values for field in ('start_address_id', 'return_address_id')) and not self.env.context.get(
            'of_skip_osrm_data_compute'
        ):
            tours_to_compute = self.env['of.planning.tour']
            for tour in self:
                old_values = saved_values[tour.id]
                if (
                    tour.start_address_id != old_values['start_address_id']
                    or tour.return_address_id != old_values['return_address_id']
                ):
                    tours_to_compute |= tour
            tours_to_compute and tours_to_compute.action_compute_osrm_data()

    def _handle_wizard_opening(self, wizard_model, error_message):
        """
        Handle the opening of a wizard for tour planning or reorganization.
        Does some checks before opening the wizard.

        Args:
            wizard_model (str): The model of the wizard to open.
            error_message (str): The error message to display if the wizard cannot be opened.
        """
        self.ensure_one()
        if not self.tour_line_ids:
            raise UserError(_("You can't reorganize an empty tour."))

        self._check_tour_addresses(error_message)
        self._check_employee_no_working_hours()
        self._check_interventions_addresses()
        self._osrm_recompute_data_if_needed()

        if wizard_model == 'of.planning.tour.optimization.wizard':
            lines_values = [
                Command.create(tour_line._prepare_optimization_line_values()) for tour_line in self.tour_line_ids
            ]
        else:  # of.tour.planning.reorganization.wizard
            lines_values = [
                Command.create(tour_line._prepare_reoganization_line_values()) for tour_line in self.tour_line_ids
            ]

        return self.env[wizard_model].create(
            {
                'tour_id': self.id,
                'line_ids': lines_values,
            }
        )

    @api.model
    def _create_tours_for_employees(self, employees, dates_eval, address_sector):
        """
        Create or update tours for a list of employees on specified dates.

        This method iterates over the provided employees and dates, and for each combination,
        it either finds an existing tour or creates a new one. If an address sector is provided,
        it updates the sector information of the tour accordingly.

        Args:
            employees (list): List of employee records.
            dates_eval (list): List of dates to evaluate.
            address_sector (record): Address sector record to associate with the tours.

        Returns:
            recordset: A recordset of the created or updated tours.
        """
        tours = self.browse()
        for employee in employees:
            for date_eval in dates_eval:
                tour = self.search([('date', '=', date_eval), ('employee_id', '=', employee.id)], limit=1)
                if not tour:
                    tour = self.create(
                        {
                            'date': date_eval,
                            'employee_id': employee.id,
                            'sector_ids': [Command.set([address_sector.id])] if address_sector else False,
                        }
                    )
                elif not tour.sector_ids and address_sector:
                    tour.sector_ids = [Command.set([address_sector.id])]
                elif address_sector and address_sector.id not in tour.sector_ids.ids:
                    tour.sector_ids = [Command.link(address_sector.id)]
                tours += tour
        return tours

    @api.model
    def cron_generate_employees_tours(self, force_date=False, force_company_id=False):
        """
        Generate tours for employees for the next period of days defined in the configuration.
        At each cron execution, it will check if there are new employees created since the last execution and generate
        tours for them if needed.

        Args:
            force_date (str, optional): A specific date in the format 'YYYY-MM-DD' to force the generation of tours.
                Defaults to False.
            force_company_id (bool, optional): The ID of a specific company to generate tours for. Defaults to False.

        Returns:
            bool: True if the generation of tours is successful.
        """
        icp_obj = self.env['ir.config_parameter']
        employee_obj = self.env['hr.employee']
        days_obj = self.env['of.days']
        icp_obj = self.env['ir.config_parameter']

        new_employees = employee_obj
        today = datetime.strptime(force_date, '%Y-%m-%d').date() if force_date else datetime.now().date()

        # we are using config parameters here to avoid cron autolock during job processing
        cron_lastcreation = icp_obj.get_param(
            'of.planning.tour.cron_generate_lastcreation', datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        )
        lastcreation_d = datetime.strptime(cron_lastcreation, '%Y-%m-%d %H:%M:%S').date()

        # checking if cron has to do someting by comparing nextcall date with today
        cron_nextcall = icp_obj.get_param('of.planning.tour.cron_generate_nextcall', False)
        cron_nextcall_dt = datetime.strptime(cron_nextcall, '%Y-%m-%d %H:%M:%S') if cron_nextcall else False
        if cron_nextcall_dt and cron_nextcall_dt.strftime('%Y-%m-%d') > today.strftime('%Y-%m-%d'):
            # cron is not due to run today but if there is new created employees since the last execution we need to
            # generate tours for them
            new_employees = employee_obj.search([('create_date', '>=', cron_lastcreation)])
            if not new_employees:
                _logger.info(f"Nothing todo. Cron generate tour is scheduled for {cron_nextcall}")
                return True

        company_id = int(force_company_id) if force_company_id else False
        employee_ids = icp_obj.get_param('of.planning.tour.tour_employee_ids', '[]')
        day_ids = icp_obj.get_param('of.planning.tour.tour_day_ids', [])
        period_in_days = int(icp_obj.get_param('of.planning.tour.nbr_days_tour_creation', DEFAULT_PERIOD_IN_DAYS))
        employee_ids = ast.literal_eval(employee_ids)
        day_ids = ast.literal_eval(day_ids)

        if not new_employees:
            # get employees to process from the settings if its set, search all employees otherwise
            employee_domain = [('id', 'in', employee_ids)] if employee_ids else []
            if company_id:
                employee_domain.append('|', ('company_id', '=', company_id), ('company_id', '=', False))
            employees = employee_obj.search(employee_domain)
        elif employee_ids:
            return True  # we don't need to generate tours for new employees if we have a list of employees
        else:
            employees = new_employees

        days = days_obj.search([('id', 'in', day_ids)])
        days_number = [day.number for day in days] or range(1, 8)

        delta = timedelta(days=period_in_days)

        # generate the list of dates for which we need to generate tours on that period (with a security margin)
        tour_dates = []
        for date in [lastcreation_d + timedelta(days=i) for i in range(1, delta.days + 1 + SECURITY_MARGIN_IN_DAYS)]:
            tour_dates.append(date.strftime('%Y-%m-%d')) if date.weekday() + 1 in days_number else None

        # search existing tours for employees on this period
        if tour_dates:
            search_existing_tours = self.search(
                [('date', '>=', tour_dates[0]), ('date', '<=', tour_dates[-1]), ('employee_id', 'in', employees.ids)]
            )
            tour_by_employee = {}
            for tour in search_existing_tours:
                tour_by_employee.setdefault(tour.employee_id, []).append(tour.date)

            # generate tours for each employee for missing dates
            for employee in employees:
                employee_tour_dates = tour_dates[:]
                if tour_by_employee.get(employee):
                    employee_tour_dates = [x for x in employee_tour_dates if x not in tour_by_employee.get(employee)]

                for date in employee_tour_dates:
                    self.action_generate_tour(date, employee)

        # set the nextcall date (in x days)
        cron_nextcall_dt = datetime.strptime(cron_nextcall, '%Y-%m-%d %H:%M:%S') if cron_nextcall else datetime.now()
        cron_generate_nextcall = (cron_nextcall_dt + timedelta(days=period_in_days)).strftime('%Y-%m-%d %H:%M:%S')
        if not new_employees:  # normal cron call
            icp_obj.set_param(
                'of.planning.tour.cron_generate_lastcreation', datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            )
            icp_obj.set_param('of.planning.tour.cron_generate_nextcall', cron_generate_nextcall)
            _logger.info(f"Done. Cron generate tour is scheduled for {cron_generate_nextcall}")
        else:  # cron call for new employees
            _logger.info(
                f"Done. Cron generate tour for new employees {new_employees}."
                f" Next call is still scheduled on {cron_generate_nextcall}"
            )
        return True

    def _get_start_stop_markers_data_for_tour(self):
        """
        Get the start and stop markers data for the tour.
        They are not real interventions, just markers to display on the map to show the start and stop of the tour.

        Returns:
            tuple: A tuple containing the start marker and end marker data.
        """
        self.ensure_one()
        default_marker = {
            'id': f'fake_record_{self.id}',
            'partner_phone': False,
            'partner_mobile': False,
            'is_start_end_marker': True,
        }
        same_start_return_address = (
            self.start_address_id.partner_longitude == self.return_address_id.partner_longitude
            and self.start_address_id.partner_latitude == self.return_address_id.partner_latitude
        )
        start_marker = default_marker | {
            'tour_number': (_("Departure/Return") if same_start_return_address else _("Departure")),
            'address_city': self.start_address_id.city,
            'partner_name': self.start_address_id.name,
            'geo_lng': self.start_address_id.partner_longitude,
            'geo_lat': self.start_address_id.partner_latitude,
            'address_zip': self.start_address_id.zip,
        }

        # End of the tour
        end_marker = default_marker | {
            'id': start_marker['id'] if same_start_return_address else f'fake_record_{self.id}_end',
            'tour_number': _("Departure/Return") if same_start_return_address else _("Return"),
            'address_city': self.return_address_id.city,
            'partner_name': self.return_address_id.name,
            'geo_lng': self.return_address_id.partner_longitude,
            'geo_lat': self.return_address_id.partner_latitude,
        }
        return start_marker, end_marker

    # == Address methods ==

    def _get_start_address(self):
        """
        Get the start address for the tour.

        If the tour has a specific start address set, return that address.
        Otherwise, return the departure address of the employee or the partner address of the employee's company.

        Returns:
            recordset: The start address for the tour.
        """
        self.ensure_one()
        if self.start_address_id:
            return self.start_address_id
        return self.employee_id.of_start_address_id or self.employee_id.company_id.partner_id

    def _get_return_address(self):
        """
        Get the return address for the tour.

        If the tour has a specific return address set, return that address.
        Otherwise, return the return address of the employee or the company's partner address.

        Returns:
            recordset: The return address for the tour.
        """
        self.ensure_one()
        if self.return_address_id:
            return self.return_address_id
        return self.employee_id.of_return_address_id or self.employee_id.company_id.partner_id

    def _set_start_address(self, address=None):
        """
        Set the start address for the tour.

        Args:
            address (recordset): The address to set as the start address for the tour.
        """
        self.ensure_one()
        if not address:
            address = self._get_start_address()
        self.start_address_id = address

    def _set_return_address(self, address=None):
        """
        Set the return address for the tour.

        Args:
            address (recordset): The address to set as the return address for the tour.
        """
        self.ensure_one()
        if not address:
            address = self._get_return_address()
        self.return_address_id = address

    @api.model
    def _process_address_values(self, vals):
        """Process the address values for the tour.
            Falls back to the employee's addresses if no address is set, or the company's address if the employee has
            no address set.

        Args:
            vals (dict): The values to process.
        """
        if not vals.get('employee_id'):
            return {'start_address_id': vals.get('start_address_id'), 'return_address_id': vals.get('start_address_id')}

        employee = self.env['hr.employee'].sudo().browse(vals.get('employee_id'))
        start_address = vals.get('start_address_id', employee.of_start_address_id.id or False)
        return_address = vals.get('return_address_id', employee.of_return_address_id.id or False)
        if not start_address:
            start_address = employee.company_id.partner_id.id or False
        if not return_address:
            return_address = employee.company_id.partner_id.id or False
        if not start_address:
            start_address = self.env.user.company_id.partner_id.id or False
        if not return_address:
            return_address = self.env.user.company_id.partner_id.id or False
        return {
            'start_address_id': start_address,
            'return_address_id': return_address,
        }

    def _check_tour_addresses(self, error_message=None):
        """
        Checks if the tour addresses are valid.

        This method checks if the start and return addresses of the tour are set.
        If any of the addresses are missing, it retrieves them and handles the address change.
        If both addresses are missing, it raises a UserError with the specified error message.

        Args:
            error_message (str): The error message to display if both addresses are missing.

        Raises:
            UserError: If both the start and return addresses are missing.
        """
        handle_address_change = False
        if not self.start_address_id:
            self._get_start_address()
            handle_address_change = True
        if not self.return_address_id:
            self._get_return_address()
            handle_address_change = True
        if not self.start_address_id or not self.return_address_id:
            raise UserError(error_message)
        if handle_address_change:
            self.handle_address_change()

    def handle_address_change(self):
        """
        Handles the address change for the current record.
        This method ensures that the OSRM data is recomputed after the address change.
        """
        self.ensure_one()
        self.action_compute_osrm_data()

    def _check_interventions_addresses(self):
        """
        Checks if all interventions have addresses set and are geolocated before optimizing/reorganizing the tour.
        """
        self.ensure_one()

        if any(not line.intervention_id.of_address_id for line in self.tour_line_ids):
            raise UserError(_("You must set the address of all interventions before optimizing/reorganizing the tour."))
        if any(
            not line.intervention_id.of_address_id.partner_latitude
            and not line.intervention_id.of_address_id.partner_longitude
            for line in self.tour_line_ids
        ):
            raise UserError(_("Please geolocate all addresses before optimizing/reorganizing the tour."))
        return True

    # == Timeline, availability/unavailability, working hours methods ==

    @api.model
    def _get_employee_day_unavailability_timeline(self, date_check, interventions, employee_wh):
        """
        Get the timeline of employee unavailability for a specific day.

        Args:
            date_check (date): The date to check for unavailability.
            interventions (recordset): The interventions to check for unavailability.
            employee_wh (list): List of employee working hours.

        Returns:
            list: The timeline of employee unavailability in the format [(start, end), ...].
        """
        date_check_dt = fields.Datetime.to_datetime(date_check)
        date_local = fields.Datetime.context_timestamp(self.env.user, date_check_dt)
        nb_timeslots = len(employee_wh)

        # build timeline of unavailability
        # first unavailable slot is from 0:00 to the start of the first working hour
        timeline = [(0.0, employee_wh[0][0])]  # [(start, end), ...]
        timeline.extend((employee_wh[i - 1][1], employee_wh[i][0]) for i in range(1, nb_timeslots))
        # last unavailable slot is from the end of the last working hour to 24:00
        timeline.append((employee_wh[-1][1], 24.0))

        day_start = employee_wh[0][0]
        day_end = employee_wh[-1][1]

        # extend unavailability timeline with interventions slots
        for intervention in interventions:
            start_date_local = fields.Datetime.context_timestamp(intervention, intervention.start)
            if start_date_local.day != date_local.day:
                start_flo = day_start
            else:
                start_flo = start_date_local.hour + start_date_local.minute / 60.0 + start_date_local.second / 3600.0

            end_date_local = fields.Datetime.context_timestamp(intervention, intervention.stop)
            if end_date_local.day != date_local.day:
                end_flo = day_end
            else:
                end_flo = end_date_local.hour + end_date_local.minute / 60.0 + end_date_local.second / 3600.0

            timeline.append((start_flo, end_flo))

        timeline.sort()  # chronological order
        return timeline

    def _get_employee_working_hours(self):
        """
        Get the working hours of the employee for a specific date.

        Returns:
            A list of lists of tuples.
            Each tuple contains the start and end time of a working slot.
            If the employee has only one slot, it will be split into two slots.
            If the employee has more than two slots, they will be split into two lists based on the noon limit.
        """
        self.ensure_one()
        hours = (
            self.employee_id._get_employee_working_hours_list(self.date)[self.employee_id.id]
            if self.employee_id
            else []
        )

        if len(hours) == 1:
            # only one slot of working hours for the day, split it into two slots at half day duration
            duration = hours[0][1] - hours[0][0]
            half_day = hours[0][0] + duration / 2
            just_before_half_day = half_day - 0.01
            hours = [[(hours[0][0], just_before_half_day)], [(half_day, hours[0][1])]]
        elif len(hours) > 2:
            # more than two slots of working hours for the day, split them into two lists (morning and afternoon)
            new_hours = [[], []]
            for slot in hours:
                if slot[0] < AM_LIMIT_FLOAT:
                    new_hours[0].append(slot)
                else:
                    new_hours[1].append(slot)
            hours = new_hours
        else:  # two slots of working hours for the day
            hours = [[hours[0]], [hours[1]]]
        return hours

    def _is_working_hours_disrupted(self):
        """
        Check if the working hours are disrupted for the tour. (e.g. interventions outside the working hours)
        Returns a tuple containing a boolean indicating whether there are interventions outside the working hours,
        and the count of interventions outside the working hours.

        Returns:
            tuple: A tuple containing a boolean indicating whether there are interventions outside the working hours,
            and the count of interventions outside the working hours.

        Raises:
            UserError: If the employee has no working hours for the day of the tour.

        Example:
            is_disrupted, count = self._is_working_hours_disrupted()
        """
        self.ensure_one()
        if not self.tour_line_ids:
            return False, 0

        employee_wh = self._get_employee_working_hours()
        if len(employee_wh[0]) > 1 or len(employee_wh[1]) > 1:
            # we don't want to manage the case where the employee has more than 2 slots of working hours, they are
            # considered as complex hours and we don't check if the interventions are outside the working hours
            return False, 0

        if not employee_wh:
            raise UserError(_("Employee \"%s\" has no working hours for this day.\n") % self.employee_id.name)

        end_am = employee_wh[0][0][1]  # end of the morning
        start_pm = employee_wh[1][0][0]  # start of the afternoon

        # get the start and end hours of all interventions on tour
        interventions_dates = self.tour_line_ids.mapped(
            lambda tl: (
                fields.Datetime.context_timestamp(tl, tl.intervention_id.start),
                fields.Datetime.context_timestamp(tl, tl.intervention_id.stop),
            )
        )

        # get the hours of the interventions as float numbers
        hours_float_list = list(
            map(
                lambda idates: (
                    round(idates[0].hour + idates[0].minute / 60.0 + idates[0].second / 3600.0, 5),
                    round(idates[1].hour + idates[1].minute / 60.0 + idates[1].second / 3600.0, 5),
                ),
                interventions_dates,
            )
        )

        # check if some interventions are outside the working hours
        interventions_outside_working_hours = list(
            map(
                lambda ihours: (
                    (ihours[0] <= end_am and ihours[1] > end_am)
                    or (ihours[0] > end_am and ihours[1] < start_pm)
                    or (start_pm > ihours[0] > end_am and ihours[1] > start_pm)
                    or (ihours[0] < end_am and ihours[1] > start_pm)
                ),
                hours_float_list,
            )
        )

        return any(interventions_outside_working_hours), len(
            list(filter(lambda x: x, interventions_outside_working_hours))
        )

    def _get_float_first_tour_hour(self):
        """
        Returns the float value representing the hour of the first tour in the planning.
        The hour is calculated based on the first intervention of the tour.
        """
        self.ensure_one()
        if not self.tour_line_ids:
            return False

        first_intervention = self.tour_line_ids.sorted(key=lambda tl: tl.date_start)[0]
        start_date = fields.Datetime.context_timestamp(self, first_intervention.date_start)
        return round(start_date.hour + start_date.minute / 60.0 + start_date.second / 3600.0, 5)

    def _find_index_first_afternoon_line(self, afternoon_hours):
        """
        Finds the index of the first afternoon line in the tour.

        Args:
            afternoon_hours (list): A list of two floats representing the start and end hours of the afternoon.
            default_value: The value to return if no afternoon line is found.

        Returns:
            int: The index of the first afternoon line, or False if no afternoon line is found.
        """
        # get the dates of the interventions
        lines_dates = self.tour_line_ids.mapped(
            lambda tour_line: fields.Datetime.context_timestamp(tour_line, tour_line.date_start)
        )
        # build a list of booleans indicating if the intervention is in the afternoon
        afternoon_lines = map(
            lambda ds: round(ds.hour + ds.minute / 60.0 + ds.second / 3600.0, 5) >= afternoon_hours[0], lines_dates
        )
        try:
            return next(index for index, is_afternoon in enumerate(afternoon_lines) if is_afternoon)
        except StopIteration:
            return False

    def _get_tour_afternoon_first_hour_float(self):
        """
        Get the first hour (as a float) of the afternoon for the tour.
        For that we are building a list of start hours of interventions and then in this list, get the first hour
        after the AM_LIMIT_FLOAT by comparing the hours of the interventions.

        Returns:
            float: The first hour of the afternoon for the tour, or AM_LIMIT_FLOAT if not found.
        """
        self.ensure_one()
        if not self.tour_line_ids:
            return False

        employee_wh = self._get_employee_working_hours()
        # if the employee has complex hours, fallback to start of the afternoon hours  otherwise get the first hour
        # after the AM_LIMIT_FLOAT
        complex_hours = len(employee_wh[0]) > 1
        afternoon_hours = (
            employee_wh[1][0] if complex_hours else [h[0][0] for h in employee_wh if h[0][0] > AM_LIMIT_FLOAT]
        )
        if not afternoon_hours:
            return AM_LIMIT_FLOAT

        first_afternoon_line = self._find_index_first_afternoon_line(afternoon_hours)
        if not first_afternoon_line:
            return AM_LIMIT_FLOAT

        first_afternoon_dt = fields.Datetime.context_timestamp(  # get datetime of the first afternoon line
            self, self.tour_line_ids[first_afternoon_line].date_start
        )
        return round(  # return it as a float
            first_afternoon_dt.hour + first_afternoon_dt.minute / 60.0 + first_afternoon_dt.second / 3600.0, 5
        )

    def _check_employee_no_working_hours(self):
        """
        Check if any employee in the tour has no working hours set.
        If any employee has no working hours, raise a UserError with an appropriate message.
        """
        self.ensure_one()

        employees = self.tour_line_ids.mapped('intervention_id.of_employee_ids')
        if employees_wo_working_hours := employees.filtered(
            lambda e: not e.resource_calendar_id or not e.resource_calendar_id.attendance_ids
        ):
            if len(employees_wo_working_hours) > 1:
                message = _(
                    "Employees \"%(employees)s\" have no working hours.\n"
                    "Please set the working hours before optimizing/reorganizing the tour.",
                    employees=', '.join(employees_wo_working_hours.mapped('name')),
                )
            else:
                message = _(
                    "Employee \"%(employee)s\" has no working hours.\n"
                    "Please set the working hours before optimizing/reorganizing the tour.",
                    employee=employees_wo_working_hours.name,
                )
            raise UserError(message)
        return True

    # == Available time slots methods ==

    def _get_initial_available_slots(self, tour):
        """
        Creation of the initial available slots for this tour.

        Args:
            tour (Tour): The tour object for which to create the available slots.

        Returns:
            list: A list of dictionaries representing the available slots. Each dictionary contains
                    the 'start' and 'stop' datetime values for a slot.
        """
        available_slots = []
        if tour.date > fields.Date.today():
            user_tz = pytz.timezone(self.env.user.tz) if self.env.user.tz else pytz.utc
            for attendance in tour.mapped('employee_id.resource_calendar_id.attendance_ids').filtered(
                lambda a: a.dayofweek == str(tour.date.weekday()) and not a.week_type or a.week_type == tour.week_type
            ):
                start_time = time(hour=int(attendance.hour_from), minute=int(attendance.hour_from % 1 * 60))
                stop_time = time(hour=int(attendance.hour_to), minute=int(attendance.hour_to % 1 * 60))

                start = user_tz.localize(datetime.combine(tour.date, start_time))
                stop = user_tz.localize(datetime.combine(tour.date, stop_time))
                available_slots.append(
                    {
                        'start': start.astimezone(pytz.utc).replace(tzinfo=None),
                        'stop': stop.astimezone(pytz.utc).replace(tzinfo=None),
                    }
                )
        return available_slots

    def _populate_available_slots_recursive(self, tour, available_slots, line):
        """
        Recursively populates the available slots based on the given tour line.

        Args:
            tour (Tour): The tour object.
            available_slots (list): The list of available slots.
            line (TourLine): The tour line object.

        Returns:
            list: The list of updated available slots.
        """
        if available_slots:
            res = []
            slot = available_slots[0]
            if slot['start'] > line.date_stop or slot['stop'] < line.date_start:
                res = [slot]
            elif line.date_start <= slot['start'] and line.date_stop >= slot['stop']:
                # This tour line is superpozed with the entire available slot, so we delete it
                pass
            elif line.date_start <= slot['start']:
                # This tour line is superpozed with the start of the available slot
                slot.update({'start': line.date_stop, 'previous_tour_line_id': line.id})
                res = [slot]
            elif line.date_start > slot['start'] and line.date_stop < slot['stop']:
                # This tour line is inside of the available slot, a split is needed
                available_slots.insert(
                    1,
                    {
                        'start': line.date_stop,
                        'stop': slot['stop'],
                        'previous_tour_line_id': line.id,
                        'next_tour_line_id': slot.get('next_tour_line_id', False),
                    },
                )
                slot.update({'stop': line.date_start, 'next_tour_line_id': line.id})
                res = [slot]
            elif line.date_stop >= slot['stop']:
                # This tour line is superpozed with the end of the available slot
                slot.update({'stop': line.date_start, 'next_tour_line_id': line.id})
                res = [slot]

            recursive = self._populate_available_slots_recursive(tour, available_slots[1:], line)
            return res + recursive
        else:
            return []

    def _populate_available_slots(self, tour, available_slots):
        """
        Populates available slots to match tour lines info.

        Args:
            tour (Tour): The tour object.
            available_slots (list): The list of available slots.

        Returns:
            list: The updated list of available slots.
        """
        for line in tour.tour_line_ids:
            available_slots = self._populate_available_slots_recursive(tour, available_slots, line)
        return available_slots

    def _delete_available_slot_too_small_recursive(self, available_slots):
        """
        Recursively deletes available slots that are too small.
        We test if the remains are bigger than the minimun duration of a task.

        Args:
            available_slots (list): A list of available slots.

        Returns:
            list: A list of available slots that are big enough.
        """
        if not available_slots:
            return []

        slot_dict = available_slots[0]
        task_obj = self.env['of.planning.task']
        min_duration = task_obj._get_minimal_task_duration()

        duration = round(((slot_dict['stop'] - slot_dict['start']).total_seconds() / 3600.0), 2)
        if slot_dict.get('next_tour_line_id'):
            tour_line = self.env['of.planning.tour.line'].browse(slot_dict['next_tour_line_id'])
            duration -= tour_line.intervention_id.of_travel_duration

        # If the available slot is big enough, we keep it
        res = [slot_dict] if duration >= min_duration else []
        recursive = self._delete_available_slot_too_small_recursive(available_slots[1:])
        return res + recursive

    def _delete_available_slot_too_small(self, available_slots):
        return self._delete_available_slot_too_small_recursive(available_slots)

    @api.model
    def _update_available_slot(self, tour, available_slots):
        """
        We update the existing available slots with the new info. If there is too much slots, we archive them.
        If there is not enough, we create them.
        """
        available_slot_obj = self.env['of.planning.available.slot']
        tour_available_slots = available_slot_obj.with_context(active_test=False).search([('tour_id', '=', tour.id)])
        for slot_dict in available_slots:
            slot_dict.update({'active': True, 'tour_id': tour.id})
            if tour_available_slots:
                tour_available_slots[0].write(slot_dict)
                tour_available_slots = tour_available_slots - tour_available_slots[0]
            else:
                available_slot_obj.create(slot_dict)
        if tour_available_slots:
            tour_available_slots.write({'active': False})

    def _reorganize_available_slot(self):
        """Reorganize available slots of the tour depending on each tour lines."""
        for tour in self:
            available_slots = self._get_initial_available_slots(tour)
            available_slots = self._populate_available_slots(tour, available_slots)
            available_slots = self._delete_available_slot_too_small(available_slots)
            self._update_available_slot(tour, available_slots)

    # == OSRM methods ==

    def _osrm_get_tour_coordinates_data(self):
        """
        Retrieves the tour coordinates data.

        This method retrieves the coordinates data for the tour, including the start address, stop address,
        intervention points, and their associated hints.

        This dict of hints will be used by wizards to be able to retrieve the tour line associated to the coordinates
        because OSRM will send us this hint string in the response.

        Returns:
            tuple: A tuple containing the coordinates string and a dictionary of tour data by hint.

        Example:
            coordinates_str, tour_data_by_hint = self._osrm_get_tour_coordinates_data()
        """
        self.ensure_one()

        start_address = self._get_start_address()
        if not start_address:
            self._set_start_address(start_address)

        return_address = self._get_return_address()
        if not self.return_address_id:
            self._set_return_address(return_address)

        # Start point
        coordinates_str = f'{start_address.partner_longitude},{start_address.partner_latitude}'  # noqa
        hint = self._osrm_get_nearest_point_hint(coordinates_str)

        tour_data_by_hint = {  # dict of a hint string of each coordinates associated to the tour line
            hint: [
                {
                    'tour': self,
                    'line': False,
                    'coordinates': (start_address.partner_longitude, start_address.partner_latitude),
                    'intervention_id': False,
                    'type': 'start',
                }
            ]
        }

        # Interventions lines
        for line in self.tour_line_ids:
            coord_str = f'{line.geo_lng},{line.geo_lat}'  # noqa
            coordinates_str += f';{coord_str}'  # noqa

            hint = self._osrm_get_nearest_point_hint(coord_str)
            if not tour_data_by_hint.get(hint):
                tour_data_by_hint[hint] = []
            tour_data_by_hint[hint].append(
                {
                    'tour': self,
                    'line': line,
                    'coordinates': (line.geo_lng, line.geo_lat),
                    'intervention_id': line.intervention_id.id,
                    'type': 'intervention',
                }
            )

        # End point
        coord_str = f'{return_address.partner_longitude},{return_address.partner_latitude}'  # noqa
        hint = self._osrm_get_nearest_point_hint(coord_str)
        coordinates_str += f';{coord_str}'  # noqa
        tour_data_by_hint[hint] = [
            {
                'tour': self,
                'line': False,
                'intervention_id': False,
                'coordinates': (return_address.partner_longitude, return_address.partner_latitude),
                'type': 'end',
            }
        ]

        return coordinates_str, tour_data_by_hint

    @api.model
    def _osrm_get_base_url(self, mode='route'):
        """
        Returns the base URL for the OSRM routing service.

        Args:
            mode (str, optional): The routing mode. Defaults to 'route'.

        Returns:
            str: The base URL for the OSRM routing service.

        Raises:
            None

        """
        routing_base_url = config.get('of_routing_base_url', '')
        routing_version = config.get('of_routing_version', '')
        routing_profile = config.get('of_routing_profile', '')
        if not routing_base_url or not routing_version or not routing_profile:
            return False

        # Ensure the base URL is valid and ends with a single '/'
        parsed_base_url = urlparse(routing_base_url)
        if not parsed_base_url.scheme or not parsed_base_url.netloc:
            raise ValueError(_("Invalid OSRM base URL"))
        routing_base_url = parsed_base_url._replace(path='/').geturl()

        # Remove trailing slashes from version and profile
        routing_version = routing_version.rstrip('/')
        routing_profile = routing_profile.rstrip('/')
        full_url = f'{routing_base_url}{mode}/{routing_version}/{routing_profile}'

        # Validate the constructed URL
        parsed_full_url = urlparse(full_url)
        if not parsed_full_url.scheme or not parsed_full_url.netloc:
            raise ValueError(_("Constructed OSRM URL is not valid"))
        return full_url

    @api.model
    def _osrm_test_connection(self):
        """
        Test the connection to the OSRM server.

        This method sends a test query to the OSRM server to check if the connection is working.
        It uses the longitude and latitude values of OpenFire to construct the query.

        Returns:
            dict: The response from the OSRM server as a JSON object.

        Raises:
            UserError: If there is an error connecting to the OSRM server.
        """
        test_query = f"{self._osrm_get_base_url('nearest')}/{OPENFIRE_LNG},{OPENFIRE_LAT}.json?number=1"  # noqa
        try:
            req = requests.get(test_query, timeout=DEFAULT_TIMEOUT)
            res = req.json()
        except requests.exceptions.ConnectionError as e:
            raise UserError(_("Error connecting to OSRM server, please try again later.\n\n%s") % e) from e
        except Exception as e:
            raise UserError(_("An error has occured during the connection to the OSRM server : %s") % e) from e
        return res

    def _osrm_get_nearest_point_hint(self, coordinate=None):
        """
        Retrieves the nearest point hint for a given coordinate using the OSRM API.

        Args:
            coordinate (str): The coordinate for which to retrieve the nearest point hint.

        Returns:
            str: The nearest point hint for the given coordinate, or an empty string if the request fails or the hint
            is not available.
        """
        if coordinate is None:
            return False

        hint_query = f"{self._osrm_get_base_url('nearest')}/{coordinate}?number=1"
        try:
            req = requests.get(hint_query, timeout=DEFAULT_TIMEOUT)
            res = req.json()
        except Exception:
            res = {}
        return res.get('waypoints')[0].get('hint') if res.get('code') == 'Ok' else {}

    def _osrm_send_trip_request(self, coordinates_str=None):
        """
        Sends a trip request to the OSRM service.
        The 'trip' plugin solves the Traveling Salesman Problem using a greedy heuristic (farthest-insertion algorithm).
        So, returned path does not have to be the exact fastest one, as TSP is NP-hard it is only an approximation.

        Args:
            coordinates_str (str): A string containing the coordinates of the locations to visit.

        Returns:
            dict: A dictionary containing the response from the OSRM service.

        Raises:
            None
        """
        self.ensure_one()

        osrm_url = self._osrm_get_base_url('trip')
        if not osrm_url or not coordinates_str:
            return {}

        full_query = f'{osrm_url}/{coordinates_str}'
        full_query += '?geometries=geojson&overview=simplified&roundtrip=false&source=first&destination=last'
        # roundtrip: return to the first location, default is true but we set it to false because in some cases
        # the start and end points could be different.
        # see http://project-osrm.org/docs/v5.24.0/api/#trip-service for more details
        try:
            req = requests.get(full_query, timeout=DEFAULT_TIMEOUT)
            res = req.json()
        except Exception:
            res = {}
        return res

    def _osrm_recompute_data_if_needed(self, force=False):
        """
        Recomputes the tour data from OSRM if needed.

        Its means that the data is recomputed if :
            * The force parameter is True
            * The tour has no start or return address
            * The tour has no total distance or duration
            * At least one tour line has missing data (geometry_data, distance_one_way or duration_one_way)
            * The tour has the need_optimization_update flag set to True (
                meaning that the tour lines have been updated since the last optimization)

        Args:
            force (bool, optional):
                If True, forces the recomputation even if the data is already present. Defaults to False.
        """
        tours_address_missing = self.filtered(lambda t: not t.start_address_id or not t.return_address_id)
        for tour in tours_address_missing:
            if not tour.start_address_id:
                tour._set_start_address()
            if not tour.return_address_id:
                tour._set_return_address()
        tours_address_missing and tours_address_missing.action_compute_osrm_data()

        left_tours = self - tours_address_missing

        tours_to_compute = left_tours.filtered(
            lambda t: force
            or t.need_optimization_update
            or not t.total_distance
            or not t.total_duration
            or any(
                not line.geometry_data or not line.distance_one_way or not line.duration_one_way
                for line in t.tour_line_ids
            )
        )
        tours_to_compute and tours_to_compute.action_compute_osrm_data()

    # == MAP data ==

    def _get_center_map_coordinates(self):
        """
        Get the center coordinates for the map.

        Returns:
            tuple: A tuple containing the latitude and longitude coordinates of the center of the map.
        """
        self.ensure_one()
        return self.start_address_id.partner_latitude, self.start_address_id.partner_longitude
