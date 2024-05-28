# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models


class OFPlanningInterventionLine(models.Model):
    _inherit = "of.planning.intervention.line"

    def _get_event_pack_lines(self):
        """Helper method to get the pack lines of the product for the intervention line.
        Returns:
            recordset: The pack lines of the product.
        """
        self.ensure_one()
        if self.product_id.pack_ok:
            return self.product_id.pack_line_ids
        return self.env["of.product.pack.lines"].browse()

    def _prepare_and_append_procurement(self, group_id, procurements, line, qty):
        """
        Prepares and appends procurement orders for a given intervention line.

        This method handles both regular and pack products. For regular products,
        it falls back to the default behavior. For pack products, it processes each
        pack line to create and append procurement orders.
        """
        # Fallback to default behavior if not a pack product
        if not line.product_id.pack_ok:
            return super()._prepare_and_append_procurement(group_id, procurements, line, qty)

        # Handle pack products otherwise
        for pack_line in line._get_event_pack_lines():
            values = pack_line._prepare_procurement_values_from_line(line, group_id=group_id)
            product_qty = pack_line.quantity * (line.qty - qty)
            line_uom = pack_line.product_id.uom_id
            quant_uom = pack_line.product_id.uom_id
            product_qty, procurement_uom = line_uom._adjust_uom_quantities(product_qty, quant_uom)
            procurements.append(
                self.env["procurement.group"].Procurement(
                    pack_line.product_id,
                    product_qty,
                    procurement_uom,
                    line.intervention_id.of_address_id.property_stock_customer,
                    pack_line.product_id.display_name,
                    line.intervention_id.name,
                    line.intervention_id.of_company_id,
                    values,
                )
            )

    def _get_delivered_moves(self):
        """
        Compute the delivered moves for the intervention line.
        This method overrides the default behavior to account for product packs.

        Returns:
            recordset: A filtered recordset of move records that meet the criteria.
        """
        self.ensure_one()
        if not self.product_id.pack_ok:
            return super()._get_delivered_moves()

        # Get the moves that are done and not scrapped for the pack products
        pack_products = self._get_event_pack_lines().mapped("product_id")
        return self.move_ids.filtered(lambda m: m.state == "done" and not m.scrapped and m.product_id in pack_products)

    def _get_delivered_qty(self):
        """
        Calculate the delivered quantity of product packs.

        This method overrides the default behavior to account for product packs.
        It computes the delivered quantity based on the individual components
        required to assemble the packs.

        Returns:
            float: The total number of complete packs delivered, limited by the
                least available component.
        """
        self.ensure_one()

        # Fall back to default behavior if not a pack product
        if not self.product_id.pack_ok:
            return super()._get_delivered_qty()

        delivered_qty = {product: 0.0 for product in self._get_event_pack_lines().mapped("product_id")}
        for move in self._get_delivered_moves():
            if move.location_dest_id.usage == "customer":
                if not move.origin_returned_move_id or move.to_refund:
                    delivered_qty[move.product_id] += move.product_uom._compute_quantity(
                        move.product_uom_qty, move.product_id.uom_id
                    )
            elif move.to_refund:
                delivered_qty[move.product_id] -= move.product_uom._compute_quantity(
                    move.product_uom_qty, move.product_id.uom_id
                )

        # Get the quantity of each component required to assemble a product pack
        # `component_quantities` is a dictionary that maps each component to its quantity per pack
        component_quantities = {packline.product_id: packline.quantity for packline in self._get_event_pack_lines()}

        # Compute the number of packs that can be assembled for each component
        packs_per_component = []
        for product, delivered in delivered_qty.items():
            required_per_pack = component_quantities.get(product, 0.0)  # required qty for this component
            if required_per_pack > 0:
                # Number of packs available for this component
                packs_available = delivered // required_per_pack  # floor division to get the integer number of packs
                packs_per_component.append(packs_available)

        # Return the minimum number of packs that can be assembled based on the delivered components
        return min(packs_per_component, default=0.0)
