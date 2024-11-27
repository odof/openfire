# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import _, api, fields, models


class CalendarEvent(models.Model):
    _inherit = "calendar.event"

    of_has_leave_warning = fields.Boolean(
        string="Leave Warning",
        compute="_compute_of_has_leave_warning",
        help="Helper field, to display warning if employee is on leave",
    )
    of_leave_warning_message = fields.Text(string="Leave Warning Message", compute="_compute_of_has_leave_warning")

    @api.depends("of_employee_ids")
    def _compute_of_has_leave_warning(self):
        leave_obj = self.env["hr.leave"].sudo()
        for event in self:
            leave_warning_message = ""
            leaves = leave_obj.search(
                [
                    ("employee_id", "in", event.of_employee_ids.ids),
                    ("state", "=", "validate"),
                    ("date_from", "<=", event.stop),
                    ("date_to", ">=", event.start),
                ]
            )
            event.of_has_leave_warning = bool(leaves)
            if leaves:
                for leave in leaves:
                    if not leave.request_unit_half and not leave.request_unit_hours:
                        leave_warning_message += _("%s is on time off from the %s to the %s\n") % (
                            leave.employee_id.name,
                            fields.Datetime.context_timestamp(leave, leave.date_from).strftime("%d/%m/%Y"),
                            fields.Datetime.context_timestamp(leave, leave.date_to).strftime("%d/%m/%Y"),
                        )
                    else:
                        leave_warning_message += _("%s is on time off the %s from %s to %s\n") % (
                            leave.employee_id.name,
                            fields.Datetime.context_timestamp(leave, leave.date_from).strftime("%d/%m/%Y"),
                            fields.Datetime.context_timestamp(leave, leave.date_from).strftime("%H:%M"),
                            fields.Datetime.context_timestamp(leave, leave.date_to).strftime("%H:%M"),
                        )
            event.of_leave_warning_message = leave_warning_message
