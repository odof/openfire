# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, models


class OFCalendarEventEquipmentLink(models.Model):
    _name = "of.calendar.event.equipment.link"
    _inherit = ["of.calendar.event.equipment.link", "of.custom.document.mixin"]

    @api.model
    def _allowed_reports(self):
        return ["of_equipment.report_equipment_link_report"]
