# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class CalendarEvent(models.Model):
    _inherit = "calendar.event"

    of_partner_latitude = fields.Float(related="of_address_id.partner_latitude", readonly=True)
    of_partner_longitude = fields.Float(related="of_address_id.partner_longitude", readonly=True)
    of_precision = fields.Selection(related="of_address_id.of_precision", readonly=True)
    of_color_map = fields.Char(compute="_compute_of_color_map", string="Color map")

    @api.depends("of_state")
    def _compute_of_color_map(self):
        """
        COLORS
        Draft       : gray
        Confirmed   : blue
        Ongoing     : orange
        Done        : green
        Other       : black
        """
        for event in self:
            if event.of_state == "draft":
                event.of_color_map = "gray"
            elif event.of_state == "confirmed":
                event.of_color_map = "blue"
            elif event.of_state == "ongoing":
                event.of_color_map = "orange"
            elif event.of_state == "done":
                event.of_color_map = "green"
            else:
                event.of_color_map = "black"
