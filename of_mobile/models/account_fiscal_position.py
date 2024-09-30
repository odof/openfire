# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models


class AccountFiscalPosition(models.Model):
    _inherit = "account.fiscal.position"

    def write(self, vals):
        res = super().write(vals)
        self.env["calendar.event"].action_update_date([("of_fiscal_position_id", "in", self.ids)])
        return res

    def unlink(self):
        self.env["calendar.event"].action_update_date([("of_fiscal_position_id", "in", self.ids)])
        return super().unlink()
