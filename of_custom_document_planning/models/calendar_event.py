# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, models


class CalendarEvent(models.Model):
    _name = 'calendar.event'
    _inherit = ['calendar.event', 'of.custom.document.mixin']

    @api.model
    def _allowed_reports(self):
        return ['of_planning.report_intervention_report', 'of_planning.report_intervention_report']
