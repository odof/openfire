# -*- coding: utf-8 -*-
from odoo import api, models


class IrUiMenu(models.Model):
    _inherit = 'ir.ui.menu'

    @api.model
    def _visible_menu_ids(self, debug=False):
        """For specific profiles, we want to change the order of views for Planning action.
        """
        menus_ids = super(IrUiMenu, self)._visible_menu_ids(debug)
        if self.user_has_groups('of_planning_view.of_group_intervention_open_calendar'):
            # removes the menu to display the good menu with the specific views order
            planning_menu = self.env.ref('of_planning.menu_of_planning_intervention_calendar')
            return menus_ids - set(planning_menu.ids)
        return menus_ids
