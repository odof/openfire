# -*- coding: utf-8 -*-

import logging

from odoo import api, models, tools, SUPERUSER_ID

_logger = logging.getLogger(__name__)


class ResGroups(models.Model):
    _inherit = 'res.groups'

    @api.model
    def _transfer_old_planning_access_rights(self):
        _logger.info(u"Transfer old rights - START")
        # - old access rights
        # goes to access
        group_lecture_siens = self.env.ref(
            'of_planning.of_group_planning_intervention_lecture_siens', raise_if_not_found=False)
        # goes to modification
        group_lecture_tout = self.env.ref(
            'of_planning.of_group_planning_intervention_lecture_tout', raise_if_not_found=False)
        group_modification_siens = self.env.ref(
            'of_planning.of_group_planning_intervention_modification_siens', raise_if_not_found=False)
        # goes to responsible
        group_modification_tout = self.env.ref(
            'of_planning.of_group_planning_intervention_modification_tout', raise_if_not_found=False)
        # if any group is missing, the transfer has been done
        if not any([group_lecture_siens, group_lecture_tout, group_modification_siens, group_modification_tout]):
            _logger.info(u"Transfer old rights - Old groups deleted")
            return

        # - new access rights | old responsible and manager groups dealt with in module of_access_control
        group_intervention_access = self.env.ref(
            'of_planning.group_planning_intervention_access', raise_if_not_found=False)
        group_intervention_modification = self.env.ref(
            'of_planning.group_planning_intervention_modification', raise_if_not_found=False)
        group_intervention_responsible = self.env.ref(
            'of_planning.group_planning_intervention_responsible', raise_if_not_found=False)
        # can't transfer if the receiving groups aren't there
        if not group_intervention_access and not group_intervention_modification and \
                not group_intervention_responsible:
            _logger.info(u"Transfer old rights - New groups not exists")
            return
        # - users
        # group_modification_tout into group_intervention_responsible
        users_responsible = group_modification_tout.with_context(active_test=False).users
        # group_modification_siens + group_lecture_tout into group_intervention_modification
        all_modification_users = group_modification_siens.with_context(active_test=False).users | \
            group_lecture_tout.with_context(active_test=False).users
        users_modification = all_modification_users - users_responsible
        # group_lecture_siens into group_intervention_access
        all_access_users = group_lecture_siens.with_context(active_test=False).users
        users_access = (all_access_users - users_modification) - users_responsible

        if group_intervention_access and users_access:
            _logger.info(u"Transfer old rights - Access : %d users" % len(users_access))
            users_lecture_list = [(4, user_id) for user_id in users_access._ids]
            group_intervention_access.write({'users': users_lecture_list})
        if group_intervention_modification and users_modification:
            _logger.info(u"Transfer old rights - Modification : %d users" % len(users_modification))
            users_modification_list = [(4, user_id) for user_id in users_modification._ids]
            group_intervention_modification.write({'users': users_modification_list})
        if group_intervention_responsible and users_responsible:
            _logger.info(u"Transfer old rights - Responsible : %d users" % len(users_responsible))
            users_responsible_list = [(4, user_id) for user_id in users_responsible._ids]
            group_intervention_responsible.write({'users': users_responsible_list})
        _logger.info(u"Transfer old rights - END")


class Menu(models.Model):
    _inherit = 'ir.ui.menu'

    @api.model
    @tools.ormcache('frozenset(self.env.user.groups_id.ids)', 'debug')
    def _visible_menu_ids(self, debug=False):
        menus = super(Menu, self)._visible_menu_ids(debug)
        if self.env.user.has_group('of_planning.group_sales_representatives_responsible') \
           and self.env.user.id != SUPERUSER_ID:
            menus.discard(self.env.ref("of_planning.menu_of_planning_configuration").id)
        return menus
