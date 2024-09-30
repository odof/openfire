# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import json

import requests
from dateutil.relativedelta import relativedelta

from odoo import api, fields, models

from odoo.addons.of_utils.models.misc import float_2_hours_minutes

ROUTES_AVAILABLE_COLORS = [
    "#0000ff",
    "#3b00f8",
    "#5300f1",
    "#6500ea",
    "#7500e3",
    "#8300db",
    "#8f00d3",
    "#9b00cb",
    "#a500c2",
    "#b000b9",
    "#b900b0",
    "#c200a5",
    "#cb009b",
    "#d3008f",
    "#db0083",
    "#e30075",
    "#ea0065",
    "#f10053",
    "#f8003b",
    "#ff0000",
]

# added fake duplicate colors because the route to first intervention will be in black (harcoded in js)
AVAILABLE_COLORS_TOUR_LINES = [
    "#0000ff",
    "#0000ff",
] + ROUTES_AVAILABLE_COLORS


class OFPlanningTourLine(models.Model):
    _name = "of.planning.tour.line"
    _description = "Tour lines for the planning"
    _order = "tour_id, sequence asc"

    active = fields.Boolean(default=True)
    sequence = fields.Integer(required=True, default=1, copy=False, index=True)
    tour_id = fields.Many2one(comodel_name="of.planning.tour", string="Tour", required=True, ondelete="cascade")
    intervention_id = fields.Many2one(comodel_name="calendar.event", string="Intervention", ondelete="cascade")

    # Geographical data
    geo_lat = fields.Float(string="Latitude", readonly=True)
    geo_lng = fields.Float(string="Longitude", readonly=True)
    geodata_update_date = fields.Datetime(
        string="Geodata update date", readonly=True, help="Technical field to know the last update date of line geodata"
    )
    address_city = fields.Char(string="City", readonly=True)
    previous_geo_lat = fields.Float(string="Latitude of the previous point", compute="_compute_line_data")
    previous_geo_lng = fields.Float(string="Longitude of the previous point", compute="_compute_line_data")
    next_geo_lat = fields.Float(string="Latitude of the next point", compute="_compute_line_data")
    next_geo_lng = fields.Float(string="Longitude of the next point", compute="_compute_line_data")
    is_first_line_of_tour = fields.Boolean(string="First line of the tour", compute="_compute_line_data")
    is_last_line_of_tour = fields.Boolean(string="Last line of the tour", compute="_compute_line_data")
    hexa_color = fields.Char(string="Color", compute="_compute_line_data")
    duration_one_way = fields.Float(string="Trip (h)", copy=False)
    distance_one_way = fields.Float(string="Distance (km)", copy=False)
    map_latitude = fields.Text(related="tour_id.map_latitude", string="Latitude (map)", readonly=True)
    map_longitude = fields.Text(related="tour_id.map_longitude", string="Longitude (map)", readonly=True)

    # Intervention related data
    address_id = fields.Many2one(related="intervention_id.of_address_id", string="Address", readonly=True)
    date_start = fields.Datetime(related="intervention_id.start", string="Start date", readonly=True)
    date_stop = fields.Datetime(related="intervention_id.stop", string="End date", readonly=True)
    employee_ids = fields.Many2many(related="intervention_id.of_employee_ids", string="Employees", readonly=True)
    is_flexible = fields.Boolean(related="intervention_id.of_is_flexible", string="Flexible", readonly=True)
    duration = fields.Float(related="intervention_id.duration", string="Duration", readonly=True)
    task_name = fields.Char(related="intervention_id.of_task_id.name", readonly=True, string="Task")
    partner_name = fields.Char(related="intervention_id.of_partner_id.name", readonly=True, string="Partner")
    address_zip = fields.Char(related="intervention_id.of_address_id.zip", readonly=True)
    partner_phone = fields.Char(related="intervention_id.of_partner_id.phone", readonly=True)
    partner_mobile = fields.Char(related="intervention_id.of_partner_id.mobile", readonly=True)
    tour_number = fields.Char(related="intervention_id.of_tour_number", string="Tour number", readonly=True)

    # OSRM data
    osrm_query = fields.Text(
        string="OSRM query",
        help="Technical field used to see the full OSRM query used to get the distance and duration",
    )
    geometry_data = fields.Text(
        string="Geojson data",
        help="Geojson data used to draw the line on the map between the previous and the current coordinates",
    )
    endpoint_distance = fields.Float(
        string="Distance to the endpoint (km)", help="Technical field used to get the distance to the endpoint (in km)"
    )
    endpoint_duration = fields.Float(
        string="Duration to the endpoint (hours)",
        help="Technical field used to get the duration to the endpoint (in hours)",
    )
    endpoint_geometry_data = fields.Text(
        string="Geojson data to the endpoint",
        help="Geojson data used to draw the line on the map between the last intervention and the endpoint coordinates",
    )

    # Restore intervention data from last modification
    last_modification_date = fields.Datetime(
        string="Last modification date",
        readonly=True,
        default=False,
        help="Technical field to know the date of the last modification of the line from any wizards "
        "(Optimization or Reorganization)",
    )
    date_before_modification = fields.Datetime(
        string="Date (before modification)",
        readonly=True,
        default=False,
        help="Technical field that allow restoring the intervention to the state it was before last modification of "
        "its tour line from any wizard (Optimization and Reorganization)",
    )
    date_deadline_before_modification = fields.Datetime(
        string="Date deadline (before modification)",
        readonly=True,
        default=False,
        help="Technical field that allow restoring the intervention to the state it was before last modification of "
        "its tour line from any wizard (Optimization and Reorganization)",
    )
    check_availability_before_modification = fields.Boolean(
        string="Check availability (before modification)",
        readonly=True,
        default=False,
        help="Technical field that allow restoring the intervention to the state it was before last modification of "
        "its tour line from any wizard (Optimization and Reorganization)",
    )
    force_date_before_modification = fields.Boolean(
        string="Force date (before modification)",
        readonly=True,
        default=False,
        help="Technical field that allow restoring the intervention to the state it was before last modification of "
        "its tour line from any wizard (Optimization and Reorganization)",
    )
    forced_date_before_modification = fields.Datetime(
        string="Forced date (before modification)",
        readonly=True,
        default=False,
        help="Technical field that allow restoring the intervention to the state it was before last modification of "
        "its tour line from any wizard (Optimization and Reorganization)",
    )

    # ---------------------------------------------------------
    # Compute methods
    # ---------------------------------------------------------

    def _compute_line_data(self):
        """
        Compute line data for each tour line.

        This method calculates various attributes for each tour line, such as previous and next geographical
        coordinates, whether the line is the first or last line of the tour, and assigns a color to the line based
        on its sequence.

        Returns:
            None
        """
        for line in self:  # Avoid `odoo.exceptions.CacheMiss` error
            line.previous_geo_lat = False
            line.previous_geo_lng = False
            line.next_geo_lat = False
            line.next_geo_lng = False
            line.is_first_line_of_tour = False
            line.is_last_line_of_tour = False
            line.hexa_color = False

        tours = self.mapped("tour_id")
        lines_by_tour = [tour.mapped("tour_line_ids") for tour in tours]  # Get all lines by tour

        color_padding_by_tour = {
            tour: max(len(ROUTES_AVAILABLE_COLORS) // len(tour.tour_line_ids), 1) for tour in tours
        }

        for lines in lines_by_tour:
            lines_sorted = lines.sorted(key=lambda line: (line.tour_id.id, line.sequence))  # Sort lines by sequence
            len_lines_sorted = len(lines_sorted)
            last_index = 0
            for index, line in enumerate(lines_sorted):
                # Get the previous and next line of the current line
                previous_line = self.env[self._name] if index == 0 else lines_sorted[index - 1]
                next_line = self.env[self._name] if index == len_lines_sorted - 1 else lines_sorted[index + 1]

                # Check if the current line is the first or last line of the tour
                is_first_line_of_tour = previous_line == self.env[self._name]
                is_last_line_of_tour = not next_line

                # Get the geographical coordinates of the previous and next line
                if previous_line:
                    previous_geo_lat = previous_line[-1].geo_lat
                    previous_geo_lng = previous_line[-1].geo_lng
                else:
                    previous_geo_lat = line.tour_id.start_address_id.partner_latitude
                    previous_geo_lng = line.tour_id.start_address_id.partner_longitude
                if next_line:
                    next_geo_lat = next_line[0].geo_lat
                    next_geo_lng = next_line[0].geo_lng
                else:
                    next_geo_lat = line.tour_id.return_address_id.partner_latitude
                    next_geo_lng = line.tour_id.return_address_id.partner_longitude

                # Assign a color to the line based on its sequence
                color_padding = color_padding_by_tour[line.tour_id]
                sequence = line.sequence - 1
                color_index = last_index + color_padding if sequence > 0 else last_index
                last_index = color_index  # Save the last index to use it for the next line

                # Assign the computed values to the current line
                line.previous_geo_lat = previous_geo_lat
                line.previous_geo_lng = previous_geo_lng
                line.next_geo_lat = next_geo_lat
                line.next_geo_lng = next_geo_lng
                line.is_first_line_of_tour = is_first_line_of_tour
                line.is_last_line_of_tour = is_last_line_of_tour
                line.hexa_color = AVAILABLE_COLORS_TOUR_LINES[min(color_index, len(AVAILABLE_COLORS_TOUR_LINES) - 1)]

    # ---------------------------------------------------------
    # Action methods
    # ---------------------------------------------------------

    def action_restore_intervention_date(self):
        """
        Restores the intervention date to its original values.

        This method is used to restore the intervention date of a tour line to its original values
        before any modifications were made (only last modification) from the Optimization or Reorganization wizards.
        """
        self.ensure_one()
        self.intervention_id.with_context(of_avoid_tour_process=True).write(
            {
                "start": self.date_before_modification,
                "stop": self.date_deadline_before_modification,
                "of_force_dates": self.force_date_before_modification,
            }
        )

    # ---------------------------------------------------------
    # Business methods
    # ---------------------------------------------------------

    def _get_time_slot_intervention_label(self, force_start_hour=None, force_end_hour=None):
        """
        Get the label for the time slot of the intervention.
        Used in the Optimization and Reorganization wizards to display the time slot of the intervention.

        Args:
            force_start_hour (str, optional): The forced start hour for the intervention. Defaults to None.
            force_end_hour (str, optional): The forced end hour for the intervention. Defaults to None.

        Returns:
            str: The label for the time slot of the intervention in the format 'date start_hour - end_hour'.
        """
        self.ensure_one()
        intervention = self.intervention_id
        start_hour = force_start_hour or intervention.start_time_local_str
        date_intervention = fields.Datetime.context_timestamp(intervention, intervention.start).strftime("%d/%m/%Y")
        if force_end_hour:
            end_hour = force_end_hour
        elif intervention.of_force_dates:
            end_hour = intervention.end_time_local_str
        else:
            duration = intervention.duration
            hours, minutes = float_2_hours_minutes(duration)
            end_hour = fields.Datetime.context_timestamp(
                intervention,
                intervention.start + relativedelta(hours=hours, minutes=minutes),
            ).strftime("%H:%M")
        return f"{date_intervention} {start_hour} - {end_hour}"

    def _prepare_optimization_line_values(self):
        """
        Prepare the optimization line values for the current tour line.
        """
        self.ensure_one()
        old_time_slot = self._get_time_slot_intervention_label()
        return {
            "tour_line_id": self.id,
            "intervention_id": self.intervention_id.id,
            "old_index": self.sequence,
            "old_time_slot": old_time_slot,
            "new_index": False,
            "new_time_slot": False,
            "old_duration": self.duration_one_way,
            "old_distance": self.distance_one_way,
        }

    def _prepare_reoganization_line_values(self):
        """
        Prepare data for the reorganization wizard lines.

        Returns:
            dict: The data required to create a reorganization wizard line.
        """
        self.ensure_one()
        return {
            "sequence": self.sequence,
            "old_sequence": self.sequence,
            "tour_line_id": self.id,
            "intervention_id": self.intervention_id.id,
            "address_city": self.address_city,
            "duration_one_way": self.duration_one_way,
            "distance_one_way": self.distance_one_way,
        }

    def _update_line_data_from_intervention(self):
        """Update line geodata from intervention"""
        self.ensure_one()
        data = self.tour_id._prepare_tour_line_values(0, self.intervention_id)
        self.write(
            {
                "geo_lat": data["geo_lat"],
                "geo_lng": data["geo_lng"],
                "address_city": data["address_city"],
                "geodata_update_date": data["geodata_update_date"],
            }
        )
        if self.tour_id.ignore_alert_optimization_update:  # data may be have changed, we need to reset the flag
            self.tour_id.ignore_alert_optimization_update = False

    def _osrm_update_line_data(self):
        """
        Updates OSRM data for the current line.

        This method retrieves OSRM data for the line, including distance, duration, request and geojson data.
        It then updates the corresponding fields in the line record.

        We use sudo() to bypass access rights, as the method can be bounced by a user with insufficient rights.

        For example, when a user modifies the geographical data of a intervention address, this triggers the
        recompute of the tour lines linked to it, so we update the OSRM data here.
        """
        self.ensure_one()
        self_sudo = self.sudo()

        # Get the line data from the OSRM API
        data = self._osrm_get_line_data()

        distance = data["distance"]
        duration_one_way = data["duration"]
        osrm_query = data["query"]
        geometry_data = data["geometry_data"]
        endpoint_geometry_data = data["endpoint_geometry_data"]
        endpoint_distance = data["endpoint_distance"]
        endpoint_duration = data["endpoint_duration"]

        # Update the line with the new data
        self_sudo.write(
            {
                "distance_one_way": distance,
                "duration_one_way": duration_one_way,
                "osrm_query": osrm_query,
                "geometry_data": geometry_data,
                "endpoint_geometry_data": endpoint_geometry_data,
                "endpoint_distance": endpoint_distance,
                "endpoint_duration": endpoint_duration,
            }
        )

    @api.model
    def _osrm_get_steps_data(self, full_query=None):
        """
        Retrieves the steps data from the OSRM API based on the given full_query.

        Args:
            full_query (str): The full query URL for the OSRM API. Its can be from the previous to the current point or
                from the current to the next point (if the line is the last line of the tour). Defaults to None.

        Returns:
            tuple: A tuple containing the steps data, distance, and duration.
                - steps (list): A list of steps for the route.
                - distance (float): The distance of the route in kilometers.
                - duration (float): The duration of the route in hours.
        """
        if not full_query:
            return []
        try:
            req = requests.get(full_query, timeout=10)
            res = req.json()
        except Exception:
            res = {}
        steps = []
        distance = duration = 0
        if res.get("routes"):
            route = res["routes"][0]
            distance = route["distance"] / 1000.0  # Convert to km
            duration = route["duration"] / 60.0 / 60.0  # Convert to hours
            legs = route["legs"]
            for leg in legs:
                steps += leg["steps"]
        return steps, distance, duration

    def _osrm_get_line_data(self):
        """
        Retrieves the line data from the OSRM API.

        Returns:
            dict: The data retrieved from the OSRM API, including the distance, duration, request and geojson data.
        """
        self.ensure_one()
        osrm_base_url = self.env["of.planning.tour"]._osrm_get_base_url()
        if (
            not osrm_base_url
            or (not self.geo_lat or not self.geo_lng)
            or (not self.previous_geo_lat or not self.previous_geo_lng)
            or self.env.context.get("of_avoid_osrm_calls")
        ):
            return {
                "query": False,
                "distance": 0,
                "duration": 0,
                "geometry_data": False,
                "endpoint_geometry_data": False,
                "endpoint_distance": 0,
                "endpoint_duration": 0,
            }

        endpoint_geometry_data = False
        endpoint_distance = endpoint_duration = 0

        # Get the data for the current line (from the previous to the current point)
        coords_str = f"{self.previous_geo_lng},{self.previous_geo_lat};{self.geo_lng},{self.geo_lat}"  # noqa
        full_query = f"{osrm_base_url}/{coords_str}?geometries=geojson&steps=true&overview=false"
        steps, distance, duration = self._osrm_get_steps_data(full_query)
        geometry_data = [step["geometry"] for step in steps]

        # Get the data for the endpoint (from the current to the next point)
        if self.is_last_line_of_tour:
            coords_str = f"{self.geo_lng},{self.geo_lat};{self.next_geo_lng},{self.next_geo_lat}"  # noqa
            endpoint_full_query = f"{osrm_base_url}/{coords_str}?geometries=geojson&steps=true&overview=false"
            endpoint_steps, endpoint_distance, endpoint_duration = self._osrm_get_steps_data(endpoint_full_query)
            endpoint_geometry_data = [step["geometry"] for step in endpoint_steps]

        geometry_data = geometry_data and json.dumps(geometry_data)
        endpoint_geometry_data = endpoint_geometry_data and json.dumps(endpoint_geometry_data)
        return {
            "query": full_query,
            "distance": distance,
            "duration": duration,
            "geometry_data": geometry_data,
            "endpoint_geometry_data": endpoint_geometry_data,
            "endpoint_distance": endpoint_distance,
            "endpoint_duration": endpoint_duration,
        }
