# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import datetime

from odoo import models, _


class StockPicking(models.Model):
    _inherit = "stock.picking"

    def action_replenish_all(self):
        self.ensure_one()
        warehouse = self.env['stock.warehouse'].search([('company_id', '=', self.company_id.id)], limit=1)
        for move in self.move_ids_without_package.filtered(
                lambda m: m.reserved_availability < m.product_uom_qty and m.product_id.type == 'product' and
                not m.replenished):
            uom_reference = move.product_id.uom_id
            quantity = move.product_uom._compute_quantity(
                move.product_uom_qty - move.reserved_availability, uom_reference, rounding_method='HALF-UP')
            replenishment = self.env['procurement.group'].create({})
            sale_order = move.sale_line_id.order_id
            if sale_order:
                origin = "%s (%s)" % (sale_order.name, sale_order.partner_id.name)
            else:
                origin = "Réassort manuel"
            values = {
                'warehouse_id': warehouse,
                'route_ids': False,
                'date_planned': datetime.datetime.now(),
                'group_id': replenishment,
            }
            self.env["procurement.group"].run(
                [
                    self.env["procurement.group"].Procurement(
                        move.product_id,
                        quantity,
                        move.product_id.uom_id,
                        warehouse.lot_stock_id,  # Location
                        "Approvisionnement à la contremarque",  # Name
                        origin,  # Origin
                        warehouse.company_id,
                        values,  # Values
                    )
                ]
            )
            move.replenished = True
        return True
