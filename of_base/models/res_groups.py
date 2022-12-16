# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import models, _
from odoo.exceptions import UserError


class ResGroups(models.Model):
    _inherit = 'res.groups'

    def write(self, vals):
        res = super().write(vals)
        # Ne pas autoriser l'ajout d'utilisateurs dans le groupe of_group_root_only
        group_root = self.env.ref('of_base.of_group_root_only', raise_if_not_found=False)
        if group_root and group_root.id in self.ids and vals.get('users'):
            if not len(group_root.users):
                raise UserError(_("The admin account cannot be removed from this group."))
            admin_user_id = self.env.ref('base.user_admin').id
            if len(group_root.users) > 1 or admin_user_id not in group_root.users.ids:
                raise UserError(_("Only the admin account can belong to this group."))
        return res
