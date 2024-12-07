# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class HrEmployee(models.Model):
    _inherit = "hr.employee"

    of_web_resource_calendar_id = fields.Many2one(
        comodel_name="resource.calendar",
        string="Web Working Hours",
        index=True,
        domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]",
    )
    of_booking_empty_days_search_max_criteria = fields.Integer(
        string="Critère de recherche max pour les journées vierges",
    )

    def write(self, vals):
        result = super().write(vals)

        # Re-calcul des tournées
        if "of_web_resource_calendar_id" in vals:
            self._recompute_tours()

        return result
