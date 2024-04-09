# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).


from odoo import models


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    def write(self, vals):
        res = super().write(vals)
        self.env['calendar.event'].action_update_date([('of_picking_ids', 'in', self.id)])
        return res

    def unlink(self):
        self.env['calendar.event'].action_update_date([('of_picking_ids', 'in', self.id)])
        return super().unlink()
