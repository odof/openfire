# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    of_order_line_option_id = fields.Many2one(comodel_name="of.order.line.option", string="Option")

    @api.onchange("of_order_line_option_id")
    def _onchange_of_order_line_option_id(self):
        """Keep an onchange here to ensure the price_unit is already changed when the option is changed
        For exemple, if the option is changed after the price unit on the line has been changed we must
        use the new price unit to compute the new price unit with the option.
        """
        if not self.of_order_line_option_id or not self.product_id:
            return
        option = self.of_order_line_option_id
        if option.sale_price_update and self.price_unit:
            if option.sale_price_update_type == "fixed":
                self.price_unit = self.price_unit + option.sale_price_update_value
            elif option.sale_price_update_type == "percent":
                self.price_unit = self.price_unit + self.price_unit * (option.sale_price_update_value / 100)
            self.price_unit = self.order_id.currency_id.round(self.price_unit)
        if option.purchase_price_update and self.purchase_price:
            if option.purchase_price_update_type == "fixed":
                self.purchase_price = self.purchase_price + option.purchase_price_update_value
            elif option.purchase_price_update_type == "percent":
                self.purchase_price = self.purchase_price + self.purchase_price * (
                    option.purchase_price_update_value / 100
                )
            self.purchase_price = self.order_id.currency_id.round(self.purchase_price)

    @api.depends("of_order_line_option_id")
    def _compute_name(self):
        super()._compute_name()
        for line in self.filtered(lambda line: line.of_order_line_option_id and line.product_id):
            option = line.of_order_line_option_id
            if option.description_update:
                line.name = self.name + "\n%s" % option.description_update

    def _purchase_service_prepare_line_values(self, purchase_order, quantity=False):
        values = super()._purchase_service_prepare_line_values(purchase_order, quantity=quantity)
        if option := self.of_order_line_option_id:
            if option.purchase_price_update:
                values["of_order_line_option_id"] = option.id
                if values["price_unit"]:
                    if option.purchase_price_update_type == "fixed":
                        values["price_unit"] = values["price_unit"] + option.purchase_price_update_value
                    elif option.purchase_price_update_type == "percent":
                        values["price_unit"] = values["price_unit"] + (
                            values["price_unit"] * (option.purchase_price_update_value / 100)
                        )
                    values["price_unit"] = purchase_order.currency_id.round(values["price_unit"])
        return values

    def action_button_reset_option_form(self):
        self.ensure_one()
        self.action_button_reset_option()
        return self.action_button_open_sale_order_line()

    def action_button_reset_option(self):
        for line in self:
            product = line.product_id.with_context(
                lang=line.order_id.partner_id.lang,
                partner=line.order_id.partner_id.id,
                quantity=line.product_uom_qty,
                date=line.order_id.date_order,
                pricelist=line.order_id.pricelist_id.id,
                uom=line.product_uom.id,
            )

            if line.order_id.pricelist_id and line.order_id.partner_id:
                line.price_unit = self.env["account.tax"]._fix_tax_included_price_company(
                    line._get_display_price(), product.taxes_id, line.tax_id, line.company_id
                )
            line.purchase_price = product.get_cost()
            if line.of_order_line_option_id.description_update:
                line.name = line.name.replace("\n%s" % line.of_order_line_option_id.description_update, "")
            line.of_order_line_option_id = False
