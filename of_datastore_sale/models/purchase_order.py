from odoo import models


class PurchaseOrder(models.Model):
    _inherit = "purchase.order"

    def button_confirm(self):
        datastore_by_partner = self._ds_get_datastore_by_partner()

        line_links = self._ds_button_confirm_get_line_links(datastore_by_partner)

        res = super().button_confirm()

        if line_links:
            self._ds_button_confirm_update_links(datastore_by_partner, line_links)
        return res

    def _ds_get_datastore_by_partner(self):
        """
        Get the datastore for each partner.

        Returns:
            dict: A dictionary mapping partner IDs to their corresponding datastore records.
        """
        partner_ids = self.mapped("partner_id.id")
        datastores = self.env["of.datastore.sale"].search([("partner_ids", "in", partner_ids)])
        return {datastore.partner_ids.id: datastore for datastore in datastores}

    def _ds_button_confirm_get_line_links(self, datastore_by_partner):
        """
        Generate a dictionary mapping purchase order lines to their corresponding datastore line IDs.

        Args:
            datastore_by_partner (dict): A mapping of partner IDs to their corresponding datastore records.

        Returns:
            dict: A dictionary where keys are purchase order lines and values are the corresponding datastore line IDs.
        """
        line_links = {}
        for order in self:
            if datastore_by_partner.get(order.partner_id.id):
                for line in order.mapped("order_line"):
                    datastore_purchase_line_id = line.procurement_ids.mapped("sale_line_id.of_datastore_line_id")
                    if len(datastore_purchase_line_id) == 1 and datastore_purchase_line_id[0] > 0:
                        line_links[line] = datastore_purchase_line_id[0]
        return line_links

    def _ds_button_confirm_update_links(self, datastore_by_partner, line_links):
        """
        Updates the links between purchase order lines and their corresponding datastore records.

        Args:
            datastore_by_partner (dict): A dictionary mapping partner IDs to their corresponding
                datastore connections.
            line_links (dict): A dictionary mapping purchase order lines to their corresponding
                datastore purchase line IDs.

        Returns:
            None
        """
        for order in self:
            if datastore := datastore_by_partner.get(order.partner_id.id):
                client = datastore.of_datastore_connect()
                if not isinstance(client, str):
                    ds_po_line_obj = datastore.of_datastore_get_model(client, "purchase.order.line")

                    # Filter lines of the current order
                    order_lines = order.mapped("order_line")
                    filtered_line_link = {
                        line: datastore_purchase_line_id
                        for line, datastore_purchase_line_id in line_links.items()
                        if line in order_lines
                    }

                    for line, datastore_purchase_line_id in filtered_line_link.items():
                        moves = line.move_ids.filtered(lambda m: m.state not in ["cancel", "done"])
                        if not moves:
                            continue

                        last_move = moves[-1]
                        ds_move_id, ds_picking_id = datastore.of_datastore_func(
                            ds_po_line_obj,
                            "get_datastore_move_id",
                            [datastore_purchase_line_id],
                            [
                                ("datastore_move_id", last_move.id),
                                ("datastore_picking_id", last_move.picking_id.id),
                            ],
                        )
                        if ds_move_id:
                            last_move.write({"of_datastore_move_id": ds_move_id})
                        if ds_picking_id:
                            last_move.picking_id.write({"of_datastore_id": ds_picking_id})
