# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models, fields, api


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    of_order_line_option_id = fields.Many2one(comodel_name='of.order.line.option', string="Option")
    of_reset_option = fields.Boolean(string="Reset option")

    @api.onchange('of_order_line_option_id')
    def _onchange_of_order_line_option_id(self):
        if self.of_order_line_option_id and self.product_id:
            option = self.of_order_line_option_id
            if option.sale_price_update and self.price_unit:
                if option.sale_price_update_type == 'fixed':
                    self.price_unit = self.price_unit + option.sale_price_update_value
                elif option.sale_price_update_type == 'percent':
                    self.price_unit = self.price_unit + self.price_unit * (option.sale_price_update_value / 100)
                self.price_unit = self.order_id.currency_id.round(self.price_unit)
            if option.purchase_price_update and self.purchase_price:
                if option.purchase_price_update_type == 'fixed':
                    self.purchase_price = self.purchase_price + option.purchase_price_update_value
                elif option.purchase_price_update_type == 'percent':
                    self.purchase_price = \
                        self.purchase_price + self.purchase_price * (option.purchase_price_update_value / 100)
                self.purchase_price = self.order_id.currency_id.round(self.purchase_price)
            if option.description_update:
                self.name = self.name + "\n%s" % option.description_update

    @api.onchange('of_reset_option')
    def _onchange_of_reset_option(self):
        if self.of_reset_option:
            product = self.product_id.with_context(
                lang=self.order_id.partner_id.lang,
                partner=self.order_id.partner_id.id,
                quantity=self.product_uom_qty,
                date=self.order_id.date_order,
                pricelist=self.order_id.pricelist_id.id,
                uom=self.product_uom.id
            )

            if self.order_id.pricelist_id and self.order_id.partner_id:
                self.price_unit = self.env['account.tax']._fix_tax_included_price_company(
                    self._get_display_price(product), product.taxes_id, self.tax_id, self.company_id)
            self.purchase_price = product.get_cost()
            if self.of_order_line_option_id.description_update:
                self.name = self.name.replace("\n%s" % self.of_order_line_option_id.description_update, '')
            self.of_order_line_option_id = False
            self.of_reset_option = False
