# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models, fields, api


class StockReservation(models.Model):
    _inherit = 'stock.reservation'

    of_sale_line_id = fields.Many2one(
        comodel_name='sale.order.line', string=u"Ligne de commande", ondelete='cascade', copy=False)

    @api.model
    def _default_picking_type_id(self):
        return self.env.ref('of_stock_reserve_sale.picking_type_reserve', raise_if_not_found=False).id
