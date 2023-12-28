# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class SaleOrderTemplate(models.Model):
    _inherit = 'sale.order.template'

    of_order_type_id = fields.Many2one(comodel_name='sale.order.type', string="Order Type")
