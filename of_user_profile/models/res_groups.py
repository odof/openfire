# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import Command, models


class ResGroups(models.Model):
    _inherit = "res.groups"

    def _update_users(self, vals):
        if vals.get("users"):
            user_obj = self.env["res.users"]
            user_profiles = user_obj.browse()
            for item in vals["users"]:
                user_ids = []
                if item[0] == Command.SET:
                    user_ids = item[2]
                elif item[0] == Command.LINK:
                    user_ids = [item[1]]
                users = user_obj.browse(user_ids)
                user_profiles |= users.filtered(lambda user: user.of_is_user_profile)
                user_profiles |= users.mapped("of_user_profile_id")
            if user_profiles:
                user_profiles._update_users_linked_to_profile()

    def write(self, vals):
        res = super().write(vals)
        self._update_users(vals)
        return res
