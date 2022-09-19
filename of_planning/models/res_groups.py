# -*- coding: utf-8 -*-

from odoo import api, models, fields, _, tools


class ResGroups(models.Model):
    _inherit = 'res.groups'

    @api.model
    def _transfer_old_planning_access_rights(self):
        # - old access rights
        # goes to access
        group_lecture_siens = self.env.ref('of_planning.of_group_planning_intervention_lecture_siens',
                                           raise_if_not_found=False)
        # goes to modification
        group_lecture_tout = self.env.ref('of_planning.of_group_planning_intervention_lecture_tout',
                                          raise_if_not_found=False)
        group_modification_siens = self.env.ref('of_planning.of_group_planning_intervention_modification_siens',
                                                raise_if_not_found=False)
        # not necessary for the transfer but commented to keep it in mind
        # group_modification_tout = self.env.ref('of_planning.of_group_planning_intervention_modification_tout')
        # if any group is missing, the transfer has been done
        if not any([group_lecture_siens, group_lecture_tout, group_modification_siens]):
            return
        # goes to modification
        # - new access rights | responsible and manager dealt with in module of_access_control
        group_intervention_access = self.env.ref('of_planning.group_planning_intervention_access',
                                                 raise_if_not_found=False)
        group_intervention_modification = self.env.ref('of_planning.group_planning_intervention_modification',
                                                       raise_if_not_found=False)
        # can't transfer if the receiving groups aren't there
        if not group_intervention_access and not group_intervention_modification:
            return
        # - users
        # group_modification_tout implies group_modification_siens, only need to get users from
        # group_modification_siens + group_lecture_tout into group_intervention_modification
        users_modification = group_modification_siens.with_context(active_test=False).users | \
                             group_lecture_tout.with_context(active_test=False).users  # goes to modification
        users_access = group_lecture_siens.with_context(active_test=False).users - \
                       (group_lecture_siens.with_context(active_test=False).users & users_modification)

        if group_intervention_access and users_access:
            users_lecture_list = [(4, user_id) for user_id in users_access._ids]
            group_intervention_access.write({'users': users_lecture_list})
        if group_intervention_modification and users_modification:
            users_modification_list = [(4, user_id) for user_id in users_modification._ids]
            group_intervention_modification.write({'users': users_modification_list})



