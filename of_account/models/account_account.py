# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import _, fields, models
from odoo.exceptions import UserError


class AccountAccount(models.Model):
    _inherit = 'account.account'

    of_account_counterpart_id = fields.Many2one(comodel_name='account.account', string="Counterpart account")
    of_editable = fields.Boolean(
        string="Editable", default=True, help="A non-editable account can only be modified by the admin."
    )

    def write(self, vals):
        # It is forbidden to modify the code of an account containing entries, except for user in the special group
        if 'code' in vals and not self.env.user.has_group('of_account.of_account_can_modify_account_with_entry_lines'):
            move_line_obj = self.env['account.move.line'].sudo()
            for account in self:
                if vals['code'] != account.code and move_line_obj.search([('account_id', '=', account.id)]):
                    raise UserError(
                        _("You cannot change the code of an account that already has entries. : %s") % account.code
                    )
        return super().write(vals)
