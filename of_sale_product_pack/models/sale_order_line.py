# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import Command, api, fields, models
from odoo.fields import first
from odoo.tools import float_compare


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    of_pack_type = fields.Selection(
        selection=[("detailed", "Detailed"), ("non_detailed", "Non Detailed")],
        string="Pack Display Type (OF)",
        compute="_compute_of_pack_type",
        store=True,
        readonly=False,
    )
    of_pack_component_price = fields.Selection(
        selection=[
            ("totalized", "Calculated"),
            ("ignored", "Fixed"),
        ],
        compute="_compute_of_pack_component_price",
        store=True,
        readonly=False,
        precompute=True,
    )
    of_pack_ok = fields.Boolean(string="Pack (OF)", compute="_compute_of_pack_ok", store=True, readonly=False)
    of_pack_line_ids = fields.One2many(
        comodel_name="of.product.pack.lines",
        inverse_name="parent_product_id",
        string="Pack Products",
        compute="_compute_of_pack_line_ids",
        store=True,
        readonly=False,
        precompute=True,
        copy=True,
        help="Products that are part of this pack.",
    )

    # ---------------------------------------------------------------------
    # Compute methods
    # ---------------------------------------------------------------------

    @api.depends("product_id")
    def _compute_of_pack_ok(self):
        for record in self:
            record.of_pack_ok = record.product_id.pack_ok if record.product_id else False

    @api.depends("product_id")
    def _compute_of_pack_line_ids(self):
        for record in self:
            if record.product_id.pack_ok:
                pack_lines = record.product_id.pack_line_ids
                pack_line_ids = [
                    Command.create(
                        {
                            "product_id": line.product_id.id,
                            "quantity": line.quantity * record.product_uom_qty,
                        },
                    )
                    for line in pack_lines
                ]
                record.of_pack_line_ids = pack_line_ids
            else:
                record.of_pack_line_ids = False

    @api.depends("product_id")
    def _compute_of_pack_type(self):
        for record in self:
            if record.product_id and record.product_id.pack_ok:
                if product_template := record.product_id.product_tmpl_id:
                    pack_type_selection = self.env["sale.order.line"].fields_get(["of_pack_type"])["of_pack_type"][
                        "selection"
                    ]

                    if product_template.pack_type in [option[0] for option in pack_type_selection]:
                        record.of_pack_type = product_template.pack_type
                    else:
                        record.of_pack_type = False
            else:
                record.of_pack_type = False

    @api.depends("product_id")
    def _compute_of_pack_component_price(self):
        for record in self:
            if record.product_id and record.product_id.pack_ok:
                if product_template := record.product_id.product_tmpl_id:
                    pack_component_price_selection = self.env["sale.order.line"].fields_get(
                        ["of_pack_component_price"]
                    )["of_pack_component_price"]["selection"]

                    if product_template.pack_component_price in [
                        option[0] for option in pack_component_price_selection
                    ]:
                        record.of_pack_component_price = product_template.pack_component_price
                    else:
                        record.of_pack_component_price = False
            else:
                record.of_pack_component_price = False

    @api.depends("product_id", "product_id.pack_ok", "of_pack_line_ids", "of_pack_component_price")
    def _compute_price_unit(self):
        super()._compute_price_unit()
        for line in self:
            if line.of_pack_component_price == "totalized":
                line.price_unit = sum(
                    pack_line.product_id.lst_price * pack_line.quantity for pack_line in line.of_pack_line_ids
                )

    @api.depends("product_id", "product_id.pack_ok", "of_pack_line_ids", "of_pack_component_price")
    def _compute_purchase_price(self):
        super()._compute_purchase_price()
        for line in self:
            if line.of_pack_component_price == "totalized":
                line.purchase_price = sum(
                    pack_line.product_id.standard_price * pack_line.quantity for pack_line in line.of_pack_line_ids
                )

    # ---------------------------------------------------------------------
    # ORM methods
    # ---------------------------------------------------------------------

    def write(self, vals):
        if vals.get("of_pack_type") == "detailed":
            old_non_detailed_lines = self.filtered(lambda x: x.of_pack_type == "non_detailed" and x.of_pack_ok)
        if "of_pack_line_ids" in vals:
            # Get the values before the write to update the order lines with pack lines after the write
            values_before_write = {}
            for line in self:
                values_before_write[line] = {"lines": line.of_pack_line_ids, "product_by_id": {}}
                for pack_line in line.of_pack_line_ids:
                    values_before_write[line]["product_by_id"][pack_line] = pack_line.product_id.id
        res = super().write(vals)
        if "of_pack_line_ids" in vals:
            detailed_lines = self.filtered(lambda x: x.of_pack_type == "detailed" and x.of_pack_ok)
            detailed_lines._update_order_lines_with_pack_lines(values_before_write)
        if vals.get("of_pack_type") == "detailed":
            old_non_detailed_lines._expand_pack_line()
        new_detailed_pack_lines = self.filtered(lambda x: x.of_pack_type == "non_detailed" and x.of_pack_ok)
        new_detailed_pack_lines and new_detailed_pack_lines._remove_detailed_pack_lines()
        return res

    # ---------------------------------------------------------------------
    # Business methods
    # ---------------------------------------------------------------------

    def _action_launch_stock_rule(self, previous_product_uom_qty=False):
        """
        Override of `_action_launch_stock_rule` to manage the procurement of pack lines :
            * If the pack line is a detailed pack, we don't want to create a move line for the pack product.
            Only for the components that are already existing sale order lines, so we skip the pack product.
            * If the pack line is a non detailed pack (pack product), sale order lines don't exist for the pack lines,
            so we create a procurement for each of them.

        Args:
            previous_product_uom_qty (bool): The previous product UOM quantity.
        """
        if self._context.get("skip_procurement"):
            return True
        precision = self.env["decimal.precision"].precision_get("Product Unit of Measure")
        procurements = []
        for line in self:
            line = line.with_company(line.company_id)
            if line.state != "sale" or line.product_id.type not in (
                "consu",
                "product",
            ):
                continue
            qty = line._get_qty_procurement(previous_product_uom_qty)
            if float_compare(qty, line.product_uom_qty, precision_digits=precision) == 0:
                continue

            group_id = line._get_procurement_group()
            if not group_id:
                group_id = self.env["procurement.group"].create(line._prepare_procurement_group_vals())
                line.order_id.procurement_group_id = group_id
            else:
                # In case the procurement group is already created and the order was
                # cancelled, we need to update certain values of the group.
                updated_vals = {}
                if group_id.partner_id != line.order_id.partner_shipping_id:
                    updated_vals["partner_id"] = line.order_id.partner_shipping_id.id
                if group_id.move_type != line.order_id.picking_policy:
                    updated_vals["move_type"] = line.order_id.picking_policy
                if updated_vals:
                    group_id.write(updated_vals)

            # if its a detailed pack, we don't want to create a move line for the pack product.
            # we wants to create a move only for the components that are already existing sale order lines,
            # so we skip the pack product line.
            if line.product_id.pack_ok and line.of_pack_type == "detailed":
                continue

            # if its a non detailed pack, sale order lines don't exist for the pack lines, so we create a procurement
            # for each of them
            if line.product_id.pack_ok and line.of_pack_type == "non_detailed":
                for pack_line in line.of_pack_line_ids:
                    values = pack_line._prepare_procurement_values(group_id=group_id)
                    product_qty = pack_line.quantity
                    line_uom = pack_line.product_id.uom_id
                    quant_uom = pack_line.product_id.uom_id
                    product_qty, procurement_uom = line_uom._adjust_uom_quantities(product_qty, quant_uom)
                    procurements.append(
                        self.env["procurement.group"].Procurement(
                            pack_line.product_id,
                            product_qty,
                            procurement_uom,
                            line.order_id.partner_shipping_id.property_stock_customer,
                            pack_line.product_id.display_name,
                            line.order_id.name,
                            line.order_id.company_id,
                            values,
                        )
                    )
            else:  # if its not a pack product keep the original behavior
                values = line._prepare_procurement_values(group_id=group_id)
                product_qty = line.product_uom_qty - qty

                line_uom = line.product_uom
                quant_uom = line.product_id.uom_id
                product_qty, procurement_uom = line_uom._adjust_uom_quantities(product_qty, quant_uom)
                procurements.append(
                    self.env["procurement.group"].Procurement(
                        line.product_id,
                        product_qty,
                        procurement_uom,
                        line.order_id.partner_shipping_id.property_stock_customer,
                        line.product_id.display_name,
                        line.order_id.name,
                        line.order_id.company_id,
                        values,
                    )
                )
        if procurements:
            procurement_group = self.env["procurement.group"]
            if self.env.context.get("import_file"):
                procurement_group = procurement_group.with_context(import_file=False)
            procurement_group.run(procurements)

        # This next block is currently needed only because the scheduler trigger is done by picking confirmation rather
        # than stock.move confirmation
        orders = self.mapped("order_id")
        for order in orders:
            if pickings_to_confirm := order.picking_ids.filtered(lambda p: p.state not in ["cancel", "done"]):
                # Trigger the Scheduler for Pickings
                pickings_to_confirm.action_confirm()
        return True

    def expand_pack_line(self, write=False):
        """
        Replacement of the OCA `expand_pack_line` function that was based on the components of a pack present
        on the product form and not on the sales order line as desired.
        """
        self.ensure_one()
        if self.of_pack_ok and self.pack_type == "detailed":
            # if we are using update_pricelist or checking out on ecommerce we
            # only want to update prices
            vals_list = []
            for subline in self.of_pack_line_ids:
                vals = subline.get_sale_order_line_vals(self, self.order_id)
                if write:
                    if existing_subline := first(
                        self.pack_child_line_ids.filtered(lambda child: child.product_id == subline.product_id)
                    ):
                        if self.do_no_expand_pack_lines:
                            vals.pop("product_uom_qty", None)
                            vals.pop("discount", None)
                        existing_subline.write(vals)
                    elif not self.do_no_expand_pack_lines:
                        vals_list.append(vals)
                else:
                    vals_list.append(vals)
            if vals_list:
                self.create(vals_list)

    def _expand_pack_line(self):
        for line in self:
            if vals_list := [line._get_pack_line_vals(line, sol_pack_line) for sol_pack_line in line.of_pack_line_ids]:
                self.create(vals_list)

    @api.model
    def _get_pack_line_vals(self, order_line, pack_line):
        """
        Get the values for the pack line.

        Args:
            pack_line (of.product.pack.lines): The pack line.
            line (sale.order.line): The order line.
            order (sale.order): The sale order.

        Returns:
            dict: The values for the pack line.
        """
        sol = self.new(
            {
                "order_id": order_line.order_id.id,
                "sequence": order_line.sequence,
                "product_id": pack_line.product_id.id,
                "product_uom_qty": pack_line.quantity * order_line.product_uom_qty,
                "price_unit": pack_line.product_id.lst_price,
                "pack_parent_line_id": order_line.id,
                "pack_modifiable": order_line.product_id.pack_modifiable,
            }
        )
        sol._onchange_product_id_warning()
        vals = sol._convert_to_write(sol._cache)
        if order_line.of_pack_type == "detailed" and order_line.product_id.pack_component_price in {
            "totalized",
            "ignored",
        }:
            vals["price_unit"] = 0.0
        vals.update({"name": f'{"> " * (order_line.pack_depth + 1)}{sol.name}'})
        return vals

    def _remove_detailed_pack_lines(self):
        self.mapped("pack_child_line_ids").unlink()

    def _update_order_lines_with_pack_lines(self, values_before_write=None):
        """
        Update the order lines with pack lines.
        This method adds, updates, and removes pack lines from the order lines based on the changes made to the pack
        lines.

        Args:
            values_before_write (dict): A dictionary containing the previous values of the order lines.
            - lines (set): A set of pack lines.
            - product_by_id (dict): A dictionary containing the product ID of the pack lines.

        Returns:
            None
        """
        for line in self:
            pack_lines = line.of_pack_line_ids

            added_items = pack_lines - values_before_write[line]["lines"]
            removed_items = values_before_write[line]["lines"] - pack_lines
            updated_items = pack_lines & values_before_write[line]["lines"]

            # Add pack lines to order lines if they don't exist
            if added_items:
                new_lines_list = [self._get_pack_line_vals(line, pack_line) for pack_line in added_items]
                self.create(new_lines_list)

            # Update pack lines in order lines if they exist
            for pack_line in updated_items:
                product_by_id = values_before_write[line]["product_by_id"][pack_line]
                li = line.pack_child_line_ids.filtered(
                    lambda ol: ol.product_id.id == product_by_id
                    and ol.product_uom_qty != (pack_line.quantity * line.product_uom_qty)
                )
                li.product_uom_qty = pack_line.quantity * line.product_uom_qty
                li.price_unit = 0.0

            # Remove pack lines from order lines if they don't exist in pack lines anymore
            order_lines_to_remove = self.browse()
            for pack_line in removed_items:
                product_by_id = values_before_write[line]["product_by_id"][pack_line]
                li = line.pack_child_line_ids.filtered(lambda ol: ol.product_id.id == product_by_id)
                order_lines_to_remove |= li
            order_lines_to_remove and order_lines_to_remove.unlink()
