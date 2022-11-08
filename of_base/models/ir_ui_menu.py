# coding: utf-8
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

# 1: imports of python lib
# 2: imports of odoo
from odoo import api, models, SUPERUSER_ID
# 3: imports from odoo modules
# 4: local imports
# 5: Import of unknown third party lib


class IrUiMenu(models.Model):
    _inherit = 'ir.ui.menu'

    @api.model
    def _visible_menu_ids(self, debug=False):
        hidden_group = self.env.ref('of_base.of_group_hidden', raise_if_not_found=False)
        menu_ids = super(IrUiMenu, self)._visible_menu_ids(debug=debug)
        if hidden_group and self._uid != SUPERUSER_ID:
            # remove all menus that are specified in the group's menu items
            return menu_ids - set(hidden_group.sudo().menu_access.ids)
        return menu_ids
