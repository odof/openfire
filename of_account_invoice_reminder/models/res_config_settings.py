# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class AccountConfigSettings(models.TransientModel):
    _inherit = 'account.config.settings'

    of_copy_reminder_date = fields.Boolean(string=u"(OF) Copier la date de dernière relance")

    @api.multi
    def set_of_copy_reminder_defaults(self):
        return self.env['ir.values'].sudo().set_default(
            'account.config.settings', 'of_copy_reminder_date', self.of_copy_reminder_date)
