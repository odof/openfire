# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    of_pack_item_price_unit_taxexcl = fields.Float(
        string="Item Unit Price Tax excl",
        compute="_compute_of_pack_price_unit",
        digits="Product Price",
        store=True,
        help="Pack Item Unit price without taxes",
    )
    of_pack_item_price_unit_taxinc = fields.Float(
        string="Item Unit Price Tax incl",
        compute="_compute_of_pack_price_unit",
        digits="Product Price",
        store=True,
        help="Pack Item Unit price with taxes",
    )
    of_pack_item_price_subtotal = fields.Monetary(
        string="Item Subtotal", compute="_compute_of_pack_amount", store=True, precompute=True
    )
    of_pack_item_price_tax = fields.Float(
        string="Item Total Tax", compute="_compute_of_pack_amount", store=True, precompute=True
    )
    of_pack_item_price_total = fields.Monetary(
        string="Item Total", compute="_compute_of_pack_amount", store=True, precompute=True
    )

    @api.depends("product_id", "pack_parent_line_id", "currency_id", "order_id.partner_shipping_id")
    def _compute_of_pack_price_unit(self):
        for line in self:
            prices = line.tax_id.compute_all(
                line.product_id.lst_price,
                currency=line.currency_id,
                quantity=1,
                product=line.product_id,
                partner=line.order_id.partner_shipping_id,
            )
            line.of_pack_item_price_unit_taxexcl = prices["total_excluded"]
            line.of_pack_item_price_unit_taxinc = prices["total_included"]

    @api.depends("product_uom_qty", "discount", "pack_parent_line_id")
    def _compute_of_pack_amount(self):
        """
        Compute the amounts of the SO line.
        """
        for line in self:
            tax_results = self.env["account.tax"]._compute_taxes([line._of_pack_convert_to_tax_base_line_dict()])
            totals = list(tax_results["totals"].values())[0]
            amount_untaxed = totals["amount_untaxed"]
            amount_tax = totals["amount_tax"]

            line.update(
                {
                    "of_pack_item_price_subtotal": amount_untaxed,
                    "of_pack_item_price_tax": amount_tax,
                    "of_pack_item_price_total": amount_untaxed + amount_tax,
                }
            )

    def _of_pack_convert_to_tax_base_line_dict(self):
        """Convert the current record to a dictionary in order to use the generic taxes computation method
        defined on account.tax.

        :return: A python dictionary.
        """
        self.ensure_one()
        return self.env["account.tax"]._convert_to_tax_base_line_dict(
            self,
            partner=self.order_id.partner_id,
            currency=self.order_id.currency_id,
            product=self.product_id,
            taxes=self.tax_id,
            price_unit=self.product_id.lst_price,
            quantity=self.product_uom_qty,
            discount=self.discount,
            price_subtotal=self.price_subtotal,
        )

    def _get_items_lines_data_to_report(self):
        self.ensure_one()
        return self.order_id.order_line.filtered(lambda line: line.pack_parent_line_id == self)
