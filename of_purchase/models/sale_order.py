# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import api, fields, models


class SaleOrder(models.Model):
    _inherit = "sale.order"

    of_delivery_expected = fields.Char(string="Expected delivery", states={"done": [("readonly", True)]})
    of_purchase_ids = fields.One2many("purchase.order", "of_sale_order_id", string="Purchases")
    of_purchase_count = fields.Integer(compute="_compute_purchase_count")
    of_user_id = fields.Many2one(comodel_name="res.users", string="Technical manager")

    @api.depends("of_purchase_ids")
    def _compute_purchase_count(self):
        for sale_order in self:
            sale_order.of_purchase_count = len(sale_order.of_purchase_ids)

    def action_view_purchases(self):
        action = self.env.ref("of_purchase.of_purchase_open_purchases").read()[0]
        action["domain"] = [("sale_order_id", "in", self._ids)]
        return action
