# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import _, models


class ProductCategory(models.Model):
    _inherit = 'product.category'

    def copy_data(self, default=None):
        new_defaults = {
            'name': _("%s (copy)") % (self.name),
        }
        default = dict(new_defaults, **(default or {}))
        return super().copy_data(default)
