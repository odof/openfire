# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models


class MailActivity(models.Model):
    _inherit = 'mail.activity'

    def action_create_calendar_event(self):
        self.ensure_one()
        action = super().action_create_calendar_event()
        action['context']['default_of_type'] = 'event'
        return action
