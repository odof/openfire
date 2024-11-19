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

    @api.model_create_multi
    def create(self, vals_list):
        employees = super().create(vals_list)

        employees._recompute_tours()

        return employees

    def write(self, vals):
        result = super().write(vals)

        # Re-calcul des tournées
        if "resource_calendar_id" in vals or vals.get("active"):
            self._recompute_tours(recompute_available_slots=True)
        elif "active" in vals:
            # Suppression des tournées à venir vides
            today = datetime.now().date()
            self.env["of.planning.tour"].search(
                [("date", ">=", today), ("employee_id", "in", self.ids), ("tour_line_ids", "=", False)]
            ).unlink()
        # Gestion du changement d'adresse
        if "of_start_address_id" in vals or "of_return_address_id" in vals:
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

        return result

    def unlink(self):
        # Empêcher la suppression des employés avec des tournées non vides
        if self.env["of.planning.tour"].search([("employee_id", "=", self.ids), ("tour_line_ids", "!=", False)]):
            raise UserError(_("You cannot delete an employee with associated interventions, archive it instead."))
        return super().unlink()

    def _recompute_tours(self, recompute_available_slots=False):
        """
        Initialize tours for employees depending of their working hours.

        Args:
            None

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

        for employee in self:
            # Génération de la liste de dates pour lesquelles des tournées doivent être créées
            work_days = employee.resource_calendar_id.attendance_ids.filtered(lambda a: not a.display_type).mapped(
                lambda a: (a.dayofweek, a.week_type)
            )
            work_days = list(set(work_days))
            tour_dates = []

            for date in [today + timedelta(days=i) for i in range(0, delta.days + 1)]:
                if ((str(date.weekday()), False) in work_days) or (
                    (str(date.weekday()), str(self.env["resource.calendar.attendance"].get_week_type(date)))
                    in work_days
                ):
                    tour_dates.append(date)

            # Contrôle des tournées existantes
            existing_tours = self.env["of.planning.tour"].search(
                [
                    ("date", ">=", today),
                    ("employee_id", "=", employee.id),
                ]
            )
            existing_tour_dates = existing_tours.mapped("date")

            new_tour_dates = tour_dates[:]

            if existing_tour_dates:
                new_tour_dates = [x for x in tour_dates if x not in existing_tour_dates]

                # Suppression des tournées vides non travaillées à venir
                existing_tours.filtered(lambda t: not t.tour_line_ids and t.date not in tour_dates).unlink()

                # Re-calcul des créneaux dispo des tournées existantes
                if recompute_available_slots:
                    existing_tours.exists()._reorganize_available_slot()

            # Création des nouvelles tournées
            vals_list = [{"employee_id": employee.id, "date": date} for date in new_tour_dates]
            self.env["of.planning.tour"].create(vals_list)

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
