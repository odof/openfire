# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import locale
from datetime import timedelta

from markupsafe import Markup

from odoo import _, api, fields, models
from odoo.tools.misc import groupby


class PlanningImpressionWizard(models.TransientModel):
    _name = "of.planning.print.wizard"
    _description = "Print Intervention Planning Wizard"

    report_type = fields.Selection(
        selection=[
            ("day", "Day"),
            ("week", "Week"),
            ("general_week", "General week"),
        ],
        string="Type",
        required=True,
        default="day",
    )
    start_date = fields.Date(required=True, default=fields.Date.today())
    stop_date = fields.Date(compute="_compute_stop_date")
    employee_ids = fields.Many2many(
        comodel_name="hr.employee",
        string="Employees",
        domain="['|', ('of_is_operator', '=', True), ('of_is_salesperson', '=', True)]",
    )
    lang = fields.Char(compute="_compute_lang", store=True, default="fr_FR")

    @api.depends("employee_ids")
    def _compute_lang(self):
        for wizard in self:
            wizard.lang = wizard.mapped("employee_ids.lang") and wizard.mapped("employee_ids.lang")[0] or "fr_FR"

    @api.depends("report_type", "start_date")
    def _compute_stop_date(self):
        for wizard in self:
            if wizard.report_type == "day":
                wizard.stop_date = wizard.start_date
            else:
                wizard.stop_date = wizard.start_date + timedelta(days=6)

    def action_button_print(self):
        self.ensure_one()
        if self.report_type == "day":
            return self.env.ref("of_planning.action_report_planning_day").report_action(self.id)
        elif self.report_type == "week":
            return self.env.ref("of_planning.action_report_planning_week").report_action(self.id)
        else:
            return self.env.ref("of_planning.action_report_planning_general_week").report_action(self.id)

    def _get_report_title(self, employee_id=False):
        employee = self.env["hr.employee"].sudo().browse(employee_id)
        self._set_locale()
        title = ""
        if self.report_type == "day":
            title = _("%s - Intervention Planning for %s") % (
                employee.name,
                self.start_date.strftime("%d %B %Y"),
            )
        elif self.report_type == "week":
            title = _("Intervention Planning - %s<br/>Week %s from %s to %s") % (
                employee.name,
                self.start_date.strftime("%W"),
                self.start_date.strftime("%d %B"),
                self.stop_date.strftime("%d %B %Y"),
            )
        elif self.report_type == "general_week":
            title = _("Intervention Planning - Week %s from %s to %s") % (
                self.start_date.strftime("%W"),
                self.start_date.strftime("%d %B"),
                self.stop_date.strftime("%d %B %Y"),
            )
        return Markup(title)

    def _get_employee_interventions(self, employee_id=False):
        """Return interventions for one employee for the week (except postponed or cancelled)"""
        if not employee_id:
            return []

        intervention_obj = self.env["calendar.event"]
        return intervention_obj.search(
            [
                ("stop", ">=", self.start_date),
                ("start", "<=", self.stop_date),
                ("of_employee_ids", "in", employee_id),
                ("of_state", "not in", ("cancel", "postponed")),
            ],
            order="start",
        )

    def _get_interventions_by_employee(self):
        """Return interventions grouped by employee and start date

        :return: dict of dict of list of interventions
        """
        intervention_obj = self.env["calendar.event"]
        res = {}
        interventions = intervention_obj.search(
            [
                ("start", ">=", self.start_date),
                ("stop", "<=", self.stop_date),
                ("of_state", "not in", ("cancel", "postponed")),
            ],
            order="start",
        )
        for employee in interventions.mapped("of_employee_ids"):
            employee_interventions = interventions.filtered(lambda interv: employee in interv.of_employee_ids)
            res[employee] = dict(groupby(employee_interventions, key=lambda interv: interv.start.date()))
        return res

    def _get_week_dates_list(self):
        """Return the next 6 days from the start date"""
        return [self.start_date + timedelta(days=day) for day in range(6)]

    def _get_intervention_datetime(self, intervention=False):
        if not intervention:
            return ""

        start_tz = fields.Datetime.context_timestamp(intervention, intervention.start)
        stop_tz = fields.Datetime.context_timestamp(intervention, intervention.stop)

        self._set_locale()
        return (
            Markup(
                _(
                    "from %(start_d)s %(start_h)s<br/>to %(stop_d)s %(stop_h)s",
                    start_d=start_tz.strftime("%a %d/%m"),
                    start_h=start_tz.strftime("%H:%M"),
                    stop_d=stop_tz.strftime("%a %d/%m"),
                    stop_h=stop_tz.strftime("%H:%M"),
                )
            )
            if intervention.start_date != intervention.stop_date
            else Markup(
                _(
                    "%(start_d)s<br/>from %(start_h)s to %(stop_h)s",
                    start_d=start_tz.strftime("%a %d/%m"),
                    start_h=start_tz.strftime("%H:%M"),
                    stop_h=stop_tz.strftime("%H:%M"),
                )
            )
        )

    def _set_locale(self):
        """Set locale for day name and month name"""
        try:
            locale.setlocale(locale.LC_TIME, self.lang)
        except locale.Error:
            locale.setlocale(locale.LC_TIME, f"{self.lang}.utf8")
