# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    of_mobile = fields.Boolean(string="Mobile Product")

    def action_button_toggle_mobile(self):
        self.ensure_one()
        self.of_mobile = not self.of_mobile
