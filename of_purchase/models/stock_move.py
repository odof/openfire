# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models


class StockMove(models.Model):
    _inherit = "stock.move"

    def _get_new_picking_values(self):
        res = super(StockMove, self)._get_new_picking_values()
        if isinstance(res, dict):
            moves = self.filtered(lambda m: m.state != "cancel")
            responsable = moves.mapped("sale_line_id").mapped("order_id").mapped("of_user_id")
            if len(responsable) == 1:
                res["of_user_id"] = responsable.id
        return res
