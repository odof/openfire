# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class ProductTemplateTag(models.Model):
    _inherit = 'product.tag'

    active = fields.Boolean(default=True)
    description = fields.Text(string="Description")
