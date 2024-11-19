# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from datetime import datetime, timedelta

from dateutil.relativedelta import relativedelta

from odoo import _, api, fields, models
from odoo.exceptions import UserError

from odoo.addons.of_planning_tour.models.of_planning_tour import DEFAULT_PERIOD_IN_MONTHS


class HrEmployee(models.Model):
    _inherit = "hr.employee"

    of_tour_ids = fields.One2many(comodel_name="of.planning.tour", inverse_name="employee_id", string="Tours")
    of_start_address_id = fields.Many2one(comodel_name="res.partner", string="Start Address")
    of_return_address_id = fields.Many2one(comodel_name="res.partner", string="Return Address")

    # -------------------------------------------------------------------------
    # ORM methods
    # -------------------------------------------------------------------------

    @api.model_create_multi
    def create(self, vals_list):
        employees = super().create(vals_list)

        employees._recompute_tours(recompute_available_slots=False)

        return employees

    def write(self, vals):
        result = super().write(vals)

        if "resource_calendar_id" in vals or vals.get("active"):
            self._recompute_tours()
        elif "active" in vals:
            self._unlink_future_empty_tours()

        if "of_start_address_id" in vals or "of_return_address_id" in vals:
            self._handle_address_change()
        return result

    def unlink(self):
        # Empêcher la suppression des employés avec des tournées non vides
        if self.env["of.planning.tour"].search([("employee_id", "=", self.ids), ("tour_line_ids", "!=", False)]):
            raise UserError(_("You cannot delete an employee with associated interventions, archive it instead."))
        return super().unlink()

    # -------------------------------------------------------------------------
    # Business methods
    # -------------------------------------------------------------------------

    def _unlink_future_empty_tours(self):
        """Unlink future tours that have no tour lines for the current employee(s)."""
        today = datetime.now().date()
        self.env["of.planning.tour"].search(
            [("date", ">=", today), ("employee_id", "in", self.ids), ("tour_line_ids", "=", False)]
        ).unlink()

    def _handle_address_change(self):
        """Handles the change of address for an employee and updates the related tours."""
        today = datetime.now().date()
        for employee in self:
            tours = self.env["of.planning.tour"].search([("date", ">=", today), ("employee_id", "=", employee.id)])
            tours.write(
                {
                    "start_address_id": employee.of_start_address_id.id,
                    "return_address_id": employee.of_return_address_id.id,
                }
            )
            tours.action_compute_osrm_data()

    def _get_employee_work_days(self):
        """
        Compute the work days for each employee based on their resource calendar.

        Returns:
            dict: A dictionary with employee IDs as keys and lists of unique work day tuples as values.
        """
        result = {}
        for employee in self:
            work_days = employee.resource_calendar_id.attendance_ids.filtered(lambda a: not a.display_type).mapped(
                lambda a: (a.dayofweek, a.week_type)
            )
            result[employee.id] = list(set(work_days))
        return result

    def _get_tour_dates_from_work_days(self, start_date, days_count, work_days):
        """
        Calculate tour dates based on work days from a given start date to a specified number of days.

        Args:
            start_date (datetime.date): The starting date of the tour.
            days_count (int): The number of days to consider from the start date.
            work_days (list of tuple): A list of tuples representing work days.
                Each tuple contains:
                    - str: The weekday as a string (0 for Monday, 6 for Sunday).
                    - str or bool: The week type or False.

        Returns:
            list of datetime.date: A list of dates that match the work days criteria.
        """
        tour_dates = []
        for date in [start_date + timedelta(days=i) for i in range(days_count + 1)]:
            if ((str(date.weekday()), False) in work_days) or (
                (str(date.weekday()), str(self.env["resource.calendar.attendance"].get_week_type(date))) in work_days
            ):
                tour_dates.append(date)
        return tour_dates

    def _recompute_tours(self, recompute_available_slots=True):
        """
        Initialize tours for employees depending of their working hours.

        Args:
            recompute_available_slots (bool): If True, recompute the available slots for the existing tours.

        Returns:
            None
        """
        period_in_months = int(
            self.env["ir.config_parameter"]
            .sudo()
            .get_param("of.planning.tour.nbr_months_tour_creation", DEFAULT_PERIOD_IN_MONTHS)
        )
        today = datetime.now().date()
        end_date = today + relativedelta(months=period_in_months)
        delta = end_date - today

        employees_work_days_dict = self._get_employee_work_days()

        for employee in self:
            # Génération de la liste de dates pour lesquelles des tournées doivent être créées
            employee_work_days = employees_work_days_dict.get(employee.id, [])

            # Récupération des dates de tournées à créer en fonction des jours travaillés de l'employé
            tour_dates = self._get_tour_dates_from_work_days(
                start_date=today, days_count=delta.days, work_days=employee_work_days
            )

            # Contrôle des tournées existantes
            existing_tours = self.env["of.planning.tour"].search(
                [
                    ("date", ">=", today),
                    ("employee_id", "=", employee.id),
                ]
            )

            new_tour_dates = tour_dates[:]
            if existing_tour_dates := existing_tours.mapped("date"):
                new_tour_dates = [x for x in tour_dates if x not in existing_tour_dates]

                # Suppression des tournées vides non travaillées à venir
                existing_tours.filtered(lambda t: not t.tour_line_ids and t.date not in tour_dates).unlink()

                # Re-calcul des créneaux dispo des tournées existantes
                if recompute_available_slots:
                    existing_tours.exists()._reorganize_available_slot()

            # Création des nouvelles tournées
            self.env["of.planning.tour"].create([{"employee_id": employee.id, "date": date} for date in new_tour_dates])

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
                lambda a: not a.display_type and a.dayofweek == str(date_eval.weekday())
            )
            sorted_attendance = attendance.sorted(key=lambda a: a.hour_from)
            workings_hours[employee.id] = [[att.hour_from, att.hour_to] for att in sorted_attendance]
        return workings_hours
