# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import fields, models


class SaleOrder(models.Model):
    _inherit = "sale.order"

    of_is_datastore_order = fields.Boolean(string="Is datastore Order ?", copy=False)
    of_datastore_purchase_id = fields.Integer(string="Order ID supplier base", copy=False)

    def action_confirm(self):
        res = super().action_confirm()
        self._ds_post_action_confirm()
        return res

    def _ds_post_action_confirm(self):
        """
        Confirms the associated purchase order in the datastore for each sale order that has a datastore purchase ID.

        Raises:
            Exception: If the connection to the datastore fails or if the confirmation process encounters an error.

        """
        for order in self.filtered("of_datastore_purchase_id"):
            if datastore := self.env["of.datastore.sale"].search([("partner_ids", "in", [order.partner_id.id])]):
                client = datastore.of_datastore_connect()
                if not isinstance(client, str):
                    ds_po_obj = datastore.of_datastore_get_model(client, "purchase.order")
                    datastore.of_datastore_func(
                        ds_po_obj, "button_confirm_xmlrpc", [order.of_datastore_purchase_id], []
                    )
