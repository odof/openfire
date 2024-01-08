# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class ResUsers(models.Model):
    _inherit = 'res.users'

    of_restricted_brand_ids = fields.Many2many(
        comodel_name='of.product.brand',
        column1='user_id',
        column2='brand_id',
        relation='of_product_brand_res_users_rel2',
        string="Unauthorized brands",
        help="Unauthorized product brands for assigned users",
    )
    of_readonly_brand_ids = fields.Many2many(
        comodel_name='of.product.brand',
        column1='res_users_id',
        column2='of_product_brand_id',
        relation='of_product_brand_res_users_rel',
        string="Unmodifiable brands",
        help="Unmodifiable product brands for assigned users",
    )
