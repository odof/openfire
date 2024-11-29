# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class CalendarEvent(models.Model):
    _inherit = "calendar.event"

    of_website_create = fields.Boolean(string="Created by website")
    of_potential_duplicated_partner = fields.Boolean(related="of_partner_id.of_potential_duplication")
