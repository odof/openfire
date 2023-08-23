# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import models


class OFAccountInvoiceReminderHook(models.AbstractModel):
    _name = 'of.account.invoice.reminder.hook'

    def _init_account_config_settings_field(self):
        module_self = self.env['ir.module.module'].search([('name', '=', 'of_account_invoice_reminder')])
        # if latest_version, module déjà installé -> ne faire l'action que dans un upgrade de version
        # if not latest_version, module pas installé -> faire l'action
        actions_todo = module_self and module_self.latest_version < '10.0.2' or not module_self.latest_version
        if actions_todo:
            if self.env['ir.values'].get_default('of.intervention.settings', 'of_copy_reminder_date') is None:
                self.env['ir.values'].set_default('account.config.settings', 'of_copy_reminder_date', True)
