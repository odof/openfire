# -*- coding: utf-8 -*-
from odoo import api, models


class IrUiMenu(models.Model):
    _inherit = 'ir.ui.menu'

    @api.model
    def _visible_menu_ids(self, debug=False):
        """For specific profiles, we want to change the order of the menu items.
        """
        menus_ids = super(IrUiMenu, self)._visible_menu_ids(debug)
        if self.user_has_groups('of_service.of_group_intervention_open_menu_maintenance'):
            # remove the menu with the highest sequence number to display the new one at the first position
            maintenance_menu = self.env.ref('of_service.of_service_maintenance_menu')
            return menus_ids - set(maintenance_menu.ids)
        return menus_ids
