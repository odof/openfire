# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, models


class AccountJournal(models.Model):
    _inherit = 'account.journal'

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        self.env['of.payment.mode'].action_update_mode_payment()
        return records

    def write(self, vals):
        res = super().write(vals)
        self.env['of.payment.mode'].action_update_mode_payment()
        return res
