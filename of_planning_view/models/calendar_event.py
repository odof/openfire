# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl

from collections import defaultdict
from datetime import timedelta

import pytz

from odoo import _, api, fields, models

from odoo.addons.resource.models.resource import Intervals, string_to_datetime, sum_intervals


class CalendarEvent(models.Model):
    _inherit = "calendar.event"

    # Planning fields
    of_planning_color = fields.Integer(
        related="of_template_id.planning_color",
        string="Planning color",
        readonly=True,
        store=True,
    )

    # Popover fields
    of_partner_address = fields.Char(
        string="Address (popover)",
        compute="_compute_popover_of_partner_address",
        help="Helper field, to display Address in the popover",
    )
    of_employees_names = fields.Char(
        string="Employees",
        compute="_compute_popover_of_employees_names",
        store=True,
        help="Helper field, to display Employees in the popover",
    )
    of_allocated_time = fields.Char(
        string="Allocated Time",
        compute="_compute_popover_of_allocated_time",
        store=True,
        help="Helper field, to display Allocated Time in the popover",
    )

    # Time allocation
    of_allocated_hours = fields.Float(
        string="Allocated Hours", compute="_compute_of_allocated_hours", store=True, readonly=False
    )
    of_allocation_type = fields.Selection(
        selection=[("planning", "Planning"), ("forecast", "Forecast")], compute="_compute_of_allocation_type"
    )
    of_allocated_percentage = fields.Float(
        string="Allocated Time %",
        default=100,
        compute="_compute_of_allocated_percentage",
        store=True,
        readonly=False,
        group_operator="avg",
    )

    # --------------------------------------------------------------------------
    # Compute methods
    # -------------------------------------------------------------------------

    def _compute_popover_of_partner_address(self):
        for event in self:
            event.of_partner_address = event.of_address_id._display_address() if event.of_address_id else ""

    @api.depends("of_employee_ids")
    def _compute_popover_of_employees_names(self):
        for event in self:
            event.of_employees_names = ", ".join(event.of_employee_ids.mapped("name"))

    @api.depends("duration")
    def _compute_popover_of_allocated_time(self):
        for event in self:
            event.of_allocated_time = str(timedelta(hours=event.duration))[:-3].zfill(5)

    @api.depends(
        "start",
        "stop",
        "of_resource_id.calendar_id",
        "of_company_id.resource_calendar_id",
        "of_allocated_percentage",
    )
    def _compute_of_allocated_hours(self):
        percentage_field = self._fields["of_allocated_percentage"]
        self.env.remove_to_compute(percentage_field, self)
        # Non allocated slots are not taken into account for the computation of allocated hours
        planning_slots = self.filtered(
            lambda s: (s.of_allocation_type == "planning" or not s.of_company_id)
            and not s.of_resource_id
            or not s.of_resource_id.calendar_id
        )
        slots_with_calendar = self - planning_slots
        for slot in planning_slots:
            # for each planning slot, compute the duration
            ratio = slot.of_allocated_percentage / 100.0
            slot.of_allocated_hours = slot._calculate_slot_duration() * ratio
        if slots_with_calendar:
            # for forecasted slots, compute the conjunction of the slot resource's work intervals and the slot.
            unplanned_slots_with_calendar = slots_with_calendar.filtered_domain(
                [
                    "|",
                    ("start", "=", False),
                    ("stop", "=", False),
                ]
            )
            # Unplanned slots will have allocated hours set to 0.0 as there are no enough information
            # to compute the allocated hours (start or end datetime are mandatory for this computation)
            for slot in unplanned_slots_with_calendar:
                slot.of_allocated_hours = 0.0
            planned_slots_with_calendar = slots_with_calendar - unplanned_slots_with_calendar
            if not planned_slots_with_calendar:
                return

            for slot in planned_slots_with_calendar:
                slot.of_allocated_hours = slot._get_duration_over_period(
                    pytz.utc.localize(slot.start),
                    pytz.utc.localize(slot.stop),
                    has_allocated_hours=False,
                )

    @api.depends("start", "stop")
    def _compute_of_allocation_type(self):
        for slot in self:
            if slot.start and slot.stop and slot.duration < 24:
                slot.of_allocation_type = "planning"
            else:
                slot.of_allocation_type = "forecast"

    @api.depends("start", "stop", "of_employee_id.resource_calendar_id", "of_allocated_hours")
    def _compute_of_allocated_percentage(self):
        # [TW:Cyclic dependency] of_allocated_hours,of_allocated_percentage
        # As of_allocated_hours and allocated percentage have some common dependencies, and are dependant one from
        # another, we have to make sure they are computed in the right order to get rid of undeterministic computation.
        #
        # Allocated percentage must only be recomputed if of_allocated_hours has been modified by the user and
        # not in any other cases.
        # If allocated hours have to be recomputed, the allocated percentage have to keep its current value.
        # Hence, we stop the computation of allocated percentage if allocated hours have to be recomputed.
        of_allocated_hours_field = self._fields["of_allocated_hours"]
        slots = self.filtered(
            lambda slot: not self.env.is_to_compute(of_allocated_hours_field, slot)
            and slot.start
            and slot.stop
            and slot.start != slot.stop
        )
        if not slots:
            return

        start_utc = pytz.utc.localize(min(slots.mapped("start")))
        end_utc = pytz.utc.localize(max(slots.mapped("stop")))
        for slot in slots:
            if not slot.of_resource_id and slot.of_allocation_type == "planning" or not slot.of_resource_id.calendar_id:
                slot.of_allocated_percentage = 100 * slot.of_allocated_hours / slot._calculate_slot_duration()
            else:
                work_hours = slot._get_working_hours_over_period(start_utc, end_utc)
                slot.of_allocated_percentage = 100 * slot.of_allocated_hours / work_hours if work_hours else 100

    # --------------------------------------------------------------------------
    # Business methods
    # --------------------------------------------------------------------------

    def _calculate_slot_duration(self):
        self.ensure_one()
        if not self.start or not self.stop:
            return 0.0
        period = self.stop - self.start
        slot_duration = period.total_seconds() / 3600
        max_duration = (period.days + 1) * self.of_company_id.resource_calendar_id.hours_per_day
        if not max_duration or max_duration >= slot_duration:
            return slot_duration
        return max_duration

    def _get_duration_over_period(self, start_utc, stop_utc, has_allocated_hours=True):
        assert start_utc.tzinfo and stop_utc.tzinfo
        self.ensure_one()
        start, stop = start_utc.replace(tzinfo=None), stop_utc.replace(tzinfo=None)
        if has_allocated_hours and self.start >= start and self.stop <= stop:
            return self.of_allocated_hours
        # if the slot goes over the planning period, compute the duration only within
        # the planning period
        ratio = self.of_allocated_percentage / 100.0
        working_hours = self._get_working_hours_over_period(start_utc, stop_utc)
        return working_hours * ratio

    def _get_working_hours_over_period(self, start_utc, end_utc):
        start = max(start_utc, pytz.utc.localize(self.start))
        end = min(end_utc, pytz.utc.localize(self.stop))
        slot_interval = Intervals([(start, end, self.env["resource.calendar.attendance"])])
        return sum_intervals(slot_interval)

    @api.model
    def planning_unavailability(self, start_date, end_date, scale, domain, group_bys=None, rows=None):
        start = fields.Datetime.from_string(start_date)
        stop = fields.Datetime.from_string(end_date)
        of_resource_ids = set()

        # function to "mark" top level rows concerning resources
        # the propagation of that item to subrows is taken care of in the traverse function below
        def tag_resource_rows(rows):
            for row in rows:
                group_bys = row.get("groupedBy")
                res_id = row.get("resId")
                if group_bys:
                    # if of_resource_id is the first grouping attribute, we mark the row
                    if group_bys[0] == "of_resource_id" and res_id:
                        of_resource_id = res_id
                        of_resource_ids.add(of_resource_id)
                        row["of_resource_id"] = of_resource_id
                    # else we recursively traverse the rows where of_resource_id appears in the group_by
                    elif "of_resource_id" in group_bys:
                        tag_resource_rows(row.get("rows"))

        tag_resource_rows(rows)
        resources = self.env["resource.resource"].browse(of_resource_ids).filtered("calendar_id")
        leaves_mapping = resources._get_unavailable_intervals(start, stop)
        company_leaves = self.env.company.resource_calendar_id._unavailable_intervals(
            start.replace(tzinfo=pytz.utc), stop.replace(tzinfo=pytz.utc)
        )

        # function to recursively replace subrows with the ones returned by func
        def traverse(func, row):
            new_row = dict(row)
            if new_row.get("of_resource_id"):
                for sub_row in new_row.get("rows"):
                    sub_row["of_resource_id"] = new_row["of_resource_id"]
            new_row["rows"] = [traverse(func, row) for row in new_row.get("rows")]
            return func(new_row)

        cell_dt = timedelta(hours=1) if scale in ["day", "week"] else timedelta(hours=12)

        # for a single row, inject unavailability data
        def inject_unavailability(row):
            new_row = dict(row)
            resource_obj = self.env["resource.resource"]

            calendar = company_leaves
            if row.get("of_resource_id"):
                of_resource_id = resource_obj.browse(row.get("of_resource_id"))
                if of_resource_id:
                    if not of_resource_id.calendar_id:
                        return new_row
                    calendar = leaves_mapping[of_resource_id.id]

            # remove intervals smaller than a cell, as they will cause half a cell to turn grey
            # ie: when looking at a week, a employee start everyday at 8, so there is a unavailability
            # like: 2019-05-22 20:00 -> 2019-05-23 08:00 which will make the first half of the 23's cell grey
            notable_intervals = filter(lambda interval: interval[1] - interval[0] >= cell_dt, calendar)
            new_row["unavailabilities"] = [
                {"start": interval[0], "stop": interval[1]} for interval in notable_intervals
            ]

            # For every resource/employee, we checked if he operates in an intervention as a secondary operator
            # so we can display on the planning that he's not unavailable but already busy
            if resource_id := row.get("of_resource_id"):
                of_resource_id = resource_obj.browse(resource_id)
                employee = of_resource_id.employee_id
                intervention_domain = [
                    ("of_employee_ids", "in", employee.ids),
                    ("of_employee_id", "!=", employee.id),
                    ("start", "<", stop),
                    ("stop", ">", start),
                ]
                intervention_domain += domain
                interventions = self.env["calendar.event"].search(intervention_domain)
                new_row["busy_time"] = [{"start": interv.start, "stop": interv.stop} for interv in interventions]
            return new_row

        return [traverse(inject_unavailability, row) for row in rows]

    def _planning_progress_bar_of_resource_id(self, res_ids, start, stop):
        start_naive, stop_naive = start.replace(tzinfo=None), stop.replace(tzinfo=None)

        resources = self.env["resource.resource"].with_context(active_test=False).search([("id", "in", res_ids)])
        interventions_slots = self.env["calendar.event"].search(
            [
                ("of_resource_id", "in", res_ids),
                ("start", "<=", stop_naive),
                ("stop", ">=", start_naive),
            ]
        )
        planned_hours_mapped = defaultdict(float)

        resource_work_intervals = resources._get_resource_work_intervals(start, stop)

        for slot in interventions_slots:
            planned_hours_mapped[slot.of_resource_id.id] += slot._get_duration_over_period(start, stop)
            # We attribute that slot duration to the employees as well
            for employee in slot.of_employee_ids:
                if employee.resource_id != slot.of_resource_id:
                    planned_hours_mapped[employee.resource_id.id] += slot._get_duration_over_period(start, stop)

        # Compute employee work hours based on its work intervals.
        work_hours = {
            of_resource_id: sum_intervals(work_intervals)
            for of_resource_id, work_intervals in resource_work_intervals.items()
        }
        return {
            resource.id: {
                "is_material_resource": resource.resource_type == "material",
                "resource_color": resource.color,
                "value": planned_hours_mapped[resource.id],
                "max_value": work_hours.get(resource.id, 0.0),
                "employee_id": resource.employee_id.id,
            }
            for resource in resources
        }

    def _planning_progress_bar(self, field, res_ids, start, stop):
        if field == "of_resource_id":
            return dict(
                self._planning_progress_bar_of_resource_id(res_ids, start, stop),
                warning=_(
                    "As there is no running contract during this period, this resource is not expected to work a shift."
                    "Planned hours:"
                ),
            )
        raise NotImplementedError(_("This Progress Bar is not implemented."))

    @api.model
    def planning_progress_bar(self, fields, res_ids, date_start_str, date_stop_str):
        if not self.user_has_groups("base.group_user"):
            return {field: {} for field in fields}

        start_utc, stop_utc = string_to_datetime(date_start_str), string_to_datetime(date_stop_str)

        return {field: self._planning_progress_bar(field, res_ids[field], start_utc, stop_utc) for field in fields}

    def _get_real_start_recursive(self, employee, start, stop):
        """Recursive function to get the first, if any, available slot for the employee between start and stop"""
        interventions = self.env["calendar.event"].search(
            [
                ("of_employee_ids", "in", [employee.id]),
                ("start", "<=", start),
                ("stop", ">", start),
                ("stop", "<", stop),
            ]
        )
        real_start = start
        if interventions:
            real_start = max(interventions.mapped("stop"))
            real_start = self._get_real_start_recursive(employee, real_start, stop)
        return real_start

    @api.model
    def get_real_start(self, resource_id, start, stop):
        resource = self.env["resource.resource"].browse(resource_id)
        employee = resource.employee_id

        return self._get_real_start_recursive(employee, start, stop)
