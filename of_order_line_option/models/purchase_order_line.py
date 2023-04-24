# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    of_order_line_option_id = fields.Many2one(comodel_name='of.order.line.option', string="Option")

    @api.onchange('of_order_line_option_id')
    def _onchange_of_order_line_option_id(self):
        """Keep an onchange here to ensure the price_unit is already changed when the option is changed.
        For exemple, if the option is changed after the price unit on the line has been changed we must
        use the new price unit to compute the new price unit with the option.
        """
        if self.of_order_line_option_id and self.product_id:
            option = self.of_order_line_option_id
            if option.purchase_price_update and self.price_unit:
                if option.purchase_price_update_type == 'fixed':
                    self.price_unit = self.price_unit + option.purchase_price_update_value
                elif option.purchase_price_update_type == 'percent':
                    self.price_unit = self.price_unit + (self.price_unit * (option.purchase_price_update_value / 100))
                self.price_unit = self.order_id.currency_id.round(self.price_unit)
            self.name = self.name + "\n%s" % option.description_update

    @api.model
    def _prepare_purchase_order_line_from_procurement(
        self, product_id, product_qty, product_uom, company_id, values, po
    ):
        result = super()._prepare_purchase_order_line_from_procurement(
            product_id, product_qty, product_uom, company_id, values, po
        )
        if values.get('sale_line_id'):
            sale_line = self.env['sale.order.line'].browse(values['sale_line_id'])
            result = self._get_sale_line_option_values(po, sale_line, result)
        return result

    def _get_sale_line_option_values(self, po=None, sale_line=None, values=None):
        """Return the values of the option of the sale line if it exists.

        :param po: The purchase order
        :param sale_line: The sale line
        :param values: The values of the purchase order line
        :return: The values of the purchase order line with the values of the option if it exists
        """
        if not values:
            values = {}
        if not sale_line or not po:
            return values
        if option := sale_line.of_order_line_option_id:
            if not values.get('of_order_line_option_id'):
                values['of_order_line_option_id'] = option.id
                if option.purchase_price_update and values['price_unit']:
                    if option.purchase_price_update_type == 'fixed':
                        values['price_unit'] = values['price_unit'] + option.purchase_price_update_value
                    elif option.purchase_price_update_type == 'percent':
                        values['price_unit'] = values['price_unit'] + (
                            values['price_unit'] * (option.purchase_price_update_value / 100)
                        )
                    values['price_unit'] = po.currency_id.round(values['price_unit'])
        return values
