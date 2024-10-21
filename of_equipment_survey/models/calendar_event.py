# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models


class CalendarEvent(models.Model):
    _inherit = "calendar.event"

    def _prepare_calendar_event_equipment_link_values_from_request_link(self, link, vals=None):
        values = super()._prepare_calendar_event_equipment_link_values_from_request_link(link, vals=vals)
        if link.equipment_report_tmpl_id:
            values["survey_id"] = link.equipment_report_tmpl_id.survey_id.id
        return values
