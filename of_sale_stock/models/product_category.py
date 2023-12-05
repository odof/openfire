# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class ProductCategory(models.Model):
    _inherit = 'product.category'

    route_ids = fields.Many2many(
        comodel_name='stock.route',
        relation='stock_location_route_categ',
        column1='categ_id',
        column2='route_id',
        string="Routes",
        domain=[('product_categ_selectable', '=', True)],
        copy=True,
    )
