# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import _, models
from odoo.exceptions import UserError

FORBIDDEN_UNINSTALL = {
    'of_base',
}


class IRModuleModule(models.Model):
    _inherit = 'ir.module.module'

    def _get_forbidden_uninstall(self):
        return FORBIDDEN_UNINSTALL

    def action_uninstall(self):
        modules = self.module_id
        modules._check_uninstall()
        return modules.button_immediate_uninstall()

    def write(self, vals):
        if vals.get('state', '') == 'to remove':
            self._check_uninstall()
        return super().write(vals)

    def button_immediate_upgrade(self):
        super().button_immediate_upgrade()
        # Dans le cadre d'une mise à jour de module, on souhaite rester sur la page courante.
        # On retourne donc une action de rechargement de la page sans spéficier de menu.
        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }

    def _check_uninstall(self):
        """Checks that the modules to be uninstalled are not base modules"""
        if illegal_uninstall := self._get_forbidden_uninstall() & set(self.mapped('name')):
            raise UserError(
                _("You are trying to delete one or more protected modules : %s") % ", ".join(illegal_uninstall)
            )
