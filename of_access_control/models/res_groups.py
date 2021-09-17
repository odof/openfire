# -*- coding: utf-8 -*-

from odoo import api, fields, models


class ResGroups(models.Model):
    _inherit = 'res.groups'

    @api.multi
    def _update_users(self, vals):
        if vals.get('users'):
            user_obj = self.env['res.users']
            user_profiles = user_obj.browse()
            for item in vals['users']:
                user_ids = []
                if item[0] == 6:
                    user_ids = item[2]
                elif item[0] == 4:
                    user_ids = [item[1]]
                users = user_obj.browse(user_ids)
                user_profiles |= users.filtered(lambda user: user.of_is_user_profile)
                user_profiles |= users.mapped('of_user_profile_id')
            if user_profiles:
                user_profiles._update_users_linked_to_profile()

    @api.multi
    def write(self, vals):
        group_ids_to_unlink = []
        group_ids_to_link = []
        if vals.get('implied_ids'):
            for item in vals['implied_ids']:
                if item[0] == 6:
                    for group in self:
                        group_ids_to_unlink.extend(list(set(group.implied_ids.ids) - set(item[2])))
                        group_ids_to_link.extend(list(set(item[2]) - set(group.implied_ids.ids)))
                elif item[0] == 5:
                    group_ids_to_unlink.extend(item[1])
                elif item[0] == 4:
                    group_ids_to_link.append(item[1])
                elif item[0] == 3:
                    group_ids_to_unlink.append(item[1])
        res = super(ResGroups, self).write(vals)
        self._update_users(vals)
        # @TODO migration : comprendre la nécessité de ce bout de code et voir si le conserver
        if vals.get('implied_ids'):
            # Update group for all users depending of this group, in order to add new implied groups to their groups
            for group in self:
                groups_id = [(4, subgroup_id) for subgroup_id in group_ids_to_link] + \
                    [(3, subgroup_id) for subgroup_id in group_ids_to_unlink]
                # Ajout d'un sudo pour pouvoir affecter le compte admin
                group.with_context(active_test=False).users.sudo().write({'groups_id': groups_id})
        return res
