# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models


class StockPicking(models.Model):
    _inherit = "stock.picking"

    def _action_done(self):
        """
        Automatically create the equipment on picking confirmation if a serial number is assigned.
        """
        res = super()._action_done()
        if (
            len(self) == 1
            and res
            and self.user_has_groups("stock.group_production_lot")
            and self.picking_type_id.code == "outgoing"
            and self.company_id.of_equipment_auto_create
        ):
            if lots := self.mapped("move_line_ids.lot_id"):
                lots.sudo().action_create_equipment(picking=self)
        return res
