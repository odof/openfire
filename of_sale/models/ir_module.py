# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models


class IRModuleModule(models.Model):
    _inherit = "ir.module.module"

    def _get_forbidden_uninstall(self):
        modules = super()._get_forbidden_uninstall()
        modules.update({"of_sale"})
        return modules
