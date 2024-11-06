# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models, fields


class CalendarEvent(models.Model):
    _inherit = 'calendar.event'

    of_website_create = fields.Boolean(string="Created by website")
