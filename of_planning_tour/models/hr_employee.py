# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class HrEmployee(models.Model):
    _inherit = "hr.employee"

    of_tour_ids = fields.One2many(comodel_name="of.planning.tour", inverse_name="employee_id", string="Tours")
    of_start_address_id = fields.Many2one(comodel_name="res.partner", string="Start Address")
    of_return_address_id = fields.Many2one(comodel_name="res.partner", string="Return Address")

    def write(self, vals):
        employees_address_changed = self._get_start_return_address_changed(vals)
        result = super().write(vals)
        if employees_address_changed:
            self._update_tours_addresses(vals, employees_address_changed)
        return result

    def _get_start_return_address_changed(self, vals):
        """
        Returns a filtered set of employees whose start or return address has changed.

        Args:
            vals (dict): A dictionary containing the updated values for the employee.

        Returns:
            filtered_set (hr_employee): A filtered set of employees whose start or return address has changed.
        """

        def _compare_address(e, vals):
            if (
                "of_address_depart_id" in vals
                and vals["of_address_depart_id"]
                and e.of_address_depart_id != vals["of_address_depart_id"]
            ):
                return True
            return bool(
                "of_address_retour_id" in vals
                and vals["of_address_retour_id"]
                and e.of_address_retour_id != vals["of_address_retour_id"]
            )

        return self.filtered(lambda e: _compare_address(e, vals))

    @api.model
    def _update_tours_addresses(self, vals, employees_address_changed):
        """
        Update tours with new address values.

        Args:
            vals (dict): A dictionary containing the updated address values.
            employees_address_changed (recordset): A recordset of employees whose addresses have changed.

        Returns:
            None
        """
        tours_to_update = self.env["of.planning.tour"].search(
            [
                ("employee_id", "in", employees_address_changed.ids),
                ("state", "!=", "3-confirmed"),
                ("date", ">=", fields.Date.today()),
            ]
        )
        # write address on tours will trigger a recomputation of OSRM route
        tour_values = {}
        if "of_address_depart_id" in vals and vals["of_address_depart_id"]:
            tour_values["start_address_id"] = vals["of_address_depart_id"]
        if "of_address_retour_id" in vals and vals["of_address_retour_id"]:
            tour_values["return_address_id"] = vals["of_address_retour_id"]
        tour_values and tours_to_update and tours_to_update.write(tour_values)

    def _get_employee_working_hours_list(self, date_eval=None, wh_type="regular"):
        """
        Get the working hours (as consecutive timeslots) list for each employee.

        Args:
            date_eval (str or None): The date to evaluate the working hours. If None, the current date is used.
            wh_type (str): The type of working hours to consider. Defaults to 'regular'.

        Returns:
            dict: A dictionary where the keys are employee IDs and the values are lists of working hours.
                Each working hour is represented as a list [hour_from, hour_to].

        Example:
            {
                1: [[8.0, 12.0], [13.0, 17.0]],
                2: [[8.0, 10.0], [11.0, 12.5], [13.5, 17.5]],
                3: [[8.0, 12.5], [13.5, 14.5], [16.5, 19.0]],
                ...
            }

        """
        if isinstance(date_eval, str):
            date_eval = fields.Date.from_string(date_eval)

        workings_hours = {employee.id: [] for employee in self}
        for employee in self:
            attendance = employee.resource_calendar_id.attendance_ids.filtered(
                lambda a: a.dayofweek == str(date_eval.weekday())
            )
            sorted_attendance = attendance.sorted(key=lambda a: a.hour_from)
            workings_hours[employee.id] = [[att.hour_from, att.hour_to] for att in sorted_attendance]
        return workings_hours
