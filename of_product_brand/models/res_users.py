# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class ResUsers(models.Model):
    _inherit = 'res.users'

    of_brand_ids = fields.Many2many(
        comodel_name='of.product.brand',
        string="Unauthorized brands",
        help="Unauthorized product brands for assigned users",
    )
