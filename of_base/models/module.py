# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import models, _
from odoo.exceptions import UserError


class Module(models.Model):
    _inherit = 'ir.module.module'

    def write(self, vals):
        if vals.get('state', '') == 'to remove':
            forbidden_uninstall = {
                'of_base,',
                'of_obligatoire',
                'of_sale',
            }
            illegal_uninstall = forbidden_uninstall & set(self.mapped('name'))
            if illegal_uninstall:
                raise UserError(
                    _("You are trying to remove one or more protected modules: %s") % ', '.join(illegal_uninstall))
        return super(Module, self).write(vals)
