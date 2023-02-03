# coding: utf-8
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, models


class AccountAccount(models.Model):
    _inherit = "account.account"

    @api.onchange('code')
    def onchange_code(self):
        group_code_obj = self.env['of.account.group.code']
        code_prefix = self.code
        # find group with longest matching prefix
        prefixes = tuple(code_prefix[:i+1] for i in xrange(len(code_prefix)))
        group = group_code_obj.search(
            [('code', 'in', prefixes),
             '|',
             ('group_id.of_account_type_ids', '=', False),
             ('group_id.of_account_type_ids', 'in', self.user_type_id.id)],
            order='code desc', limit=1).group_id
        self.group_id = group
