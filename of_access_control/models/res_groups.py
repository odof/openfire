# -*- coding: utf-8 -*-

import logging

from odoo import api, models

_logger = logging.getLogger(__name__)


class ResGroups(models.Model):
    _inherit = 'res.groups'

    @api.model
    def _transfer_old_access_control_access_rights(self):
        _logger.info(u"Transfer old rights - START")
        # - old access rights
        # goes to responsible
        group_responsible = self.env.ref(
            'of_access_control.of_group_planning_intervention_responsible', raise_if_not_found=False)
        # goes to manager
        group_manager = self.env.ref(
            'of_access_control.of_group_planning_intervention_manager', raise_if_not_found=False)
        # if any group is missing, the transfer has been done
        if not any([group_responsible, group_manager]):
            _logger.info(u"Transfer old rights - Old groups deleted")
            return
        # - new access rights | access and modification dealt with in module of_planning
        group_intervention_responsible = self.env.ref(
            'of_planning.group_planning_intervention_responsible', raise_if_not_found=False)
        group_intervention_manager = self.env.ref(
            'of_planning.group_planning_intervention_manager', raise_if_not_found=False)
        # can't transfer if the receiving groups aren't there
        if not group_intervention_responsible and not group_intervention_manager:
            _logger.info(u"Transfer old rights - New groups not exists")
            return
        # - users
        # group_manager into group_intervention_manager
        users_manager = group_manager.with_context(active_test=False).users
        # group_responsible into group_intervention_responsible
        users_responsible = group_responsible.with_context(active_test=False).users - users_manager

        if group_intervention_responsible and users_responsible:
            _logger.info(u"Transfer old rights - Responsible : %d users" % len(users_responsible))
            users_responsible_list = [(4, user_id) for user_id in users_responsible._ids]
            group_intervention_responsible.write({'users': users_responsible_list})
        if group_intervention_manager and users_manager:
            _logger.info(u"Transfer old rights - Manager : %d users" % len(users_manager))
            users_manager_list = [(4, user_id) for user_id in users_manager._ids]
            group_intervention_manager.write({'users': users_manager_list})
        _logger.info(u"Transfer old rights - END")
