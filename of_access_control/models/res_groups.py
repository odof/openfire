# -*- coding: utf-8 -*-

from odoo import api, models, fields, _, tools


class ResGroups(models.Model):
    _inherit = 'res.groups'

    @api.model
    def _transfer_old_access_control_access_rights(self):
        # - old access rights
        group_responsible = self.env.ref('of_access_control.of_group_planning_intervention_responsible',
                                         raise_if_not_found=False)
        group_manager = self.env.ref('of_access_control.of_group_planning_intervention_manager',
                                     raise_if_not_found=False)
        # if any group is missing, the transfer has been done
        if not any([group_responsible, group_manager]):
            return
        # goes to modification
        # - new access rights | responsible and manager dealt with in module of_access_control
        group_intervention_responsible = self.env.ref('of_planning.group_planning_intervention_responsible',
                                                      raise_if_not_found=False)
        group_intervention_manager = self.env.ref('of_planning.group_planning_intervention_manager',
                                                  raise_if_not_found=False)
        # can't transfer if the receiving groups aren't there
        if not group_intervention_responsible and not group_intervention_manager:
            return
        # - users
        # group_modification_tout implies group_modification_siens, only need to get users from
        # group_modification_siens + group_lecture_tout into group_intervention_modification
        users_manager = group_manager.with_context(active_test=False).users
        users_responsible = group_responsible.with_context(active_test=False).users - \
                            (group_responsible.with_context(active_test=False).users & users_manager)

        if group_intervention_responsible and users_responsible:
            users_lecture_list = [(4, user_id) for user_id in users_responsible._ids]
            group_intervention_responsible.write({'users': users_lecture_list})
        if group_intervention_manager and users_manager:
            users_modification_list = [(4, user_id) for user_id in users_manager._ids]
            group_intervention_manager.write({'users': users_modification_list})



