# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models


class ResourceCalendar(models.Model):
    _inherit = "resource.calendar"

    def write(self, vals):
        result = super(ResourceCalendar, self.with_context(of_no_tour_recompute=True)).write(vals)

        # Re-calcul des tournées
        if "attendance_ids" in vals:
            employees = self.env["hr.employee"].search([("of_web_resource_calendar_id", "in", self.ids)])
            employees._recompute_tours()

        return result
