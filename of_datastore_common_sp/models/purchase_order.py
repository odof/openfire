# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import api, fields, models


class PurchaseOrder(models.Model):
    _inherit = "purchase.order"

    of_datastore_anomaly = fields.Boolean(
        string="In Anomaly", compute="_compute_of_datastore_anomaly", search="_search_of_datastore_anomaly"
    )

    @api.depends("picking_ids", "picking_ids.of_datastore_anomaly")
    def _compute_of_datastore_anomaly(self):
        for purchase in self:
            purchase.of_datastore_anomaly = any(purchase.picking_ids.mapped("of_datastore_anomaly"))

    @api.model
    def _search_of_datastore_anomaly(self, operator, value):
        orders = (
            self.env["stock.picking"]
            .search([("of_datastore_anomaly", operator, value)])
            .mapped("move_lines")
            .mapped("procurement_id")
            .mapped("purchase_line_id")
            .mapped("order_id")
        )
        return [("id", "in", orders.ids)]
