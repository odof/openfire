# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, models


class ResourceCalendar(models.Model):
    _inherit = "resource.calendar"

    def write(self, vals):
        result = super(ResourceCalendar, self.with_context(of_no_tour_recompute=True)).write(vals)

        # Re-calcul des tournées
        if "attendance_ids" in vals:
            employees = self.env["hr.employee"].search([("resource_calendar_id", "in", self.ids)])
            employees._recompute_tours()

        return result


class ResourceCalendarAttendance(models.Model):
    _inherit = "resource.calendar.attendance"

    @api.model_create_multi
    def create(self, vals_list):
        attendances = super().create(vals_list)

        # Re-calcul des tournées
        if not self._context.get("of_no_tour_recompute"):
            employees = self.env["hr.employee"].search(
                [("resource_calendar_id", "in", attendances.mapped("calendar_id.id"))]
            )
            employees._recompute_tours()

        return attendances

    def write(self, vals):
        old_calendar_ids = self.mapped("calendar_id")

        result = super().write(vals)

        # Re-calcul des tournées
        if not self._context.get("of_no_tour_recompute"):
            employees = self.env["hr.employee"].search(
                [("resource_calendar_id", "in", (old_calendar_ids + self.mapped("calendar_id")).ids)]
            )
            employees._recompute_tours()

        return result

    def unlink(self):
        calendar_ids = self.mapped("calendar_id")

        result = super().unlink()

        # Re-calcul des tournées
        if not self._context.get("of_no_tour_recompute"):
            employees = self.env["hr.employee"].search([("resource_calendar_id", "in", calendar_ids.ids)])
            employees._recompute_tours()

        return result
