# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    of_order_requested_week = fields.Char(string="Requested week", related='order_id.of_requested_week')
