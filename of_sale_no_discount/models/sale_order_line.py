# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    of_product_forbidden_discount = fields.Boolean(
        string="Discount not allowed for this product",
        compute='_compute_of_product_forbidden_discount',
        store=True,
        readonly=False,
        precompute=True,
    )
    of_is_price_unit_readonly = fields.Boolean(
        string="Is Unit price readonly ?",
        compute='_compute_of_is_price_unit_readonly',
    )

    @api.depends('product_id')
    def _compute_of_product_forbidden_discount(self):
        for line in self:
            if line.product_id:
                line.of_product_forbidden_discount = (
                    line.product_id.of_forbidden_discount
                    or not self.env.user.has_group('of_sale_no_discount.group_of_can_modify_sale_price_unit')
                )

    @api.depends('of_product_forbidden_discount', 'of_discount_formula')
    def _compute_of_discount_formula(self):
        forbidden_discount_records = self.filtered(lambda line: line.of_product_forbidden_discount)
        for line in forbidden_discount_records:
            line.of_discount_formula = False
        super(SaleOrderLine, self - forbidden_discount_records)._compute_of_discount_formula()

    @api.depends('of_product_forbidden_discount')
    def _compute_price_unit(self):
        forbidden_discount_records = self.filtered(lambda line: line.of_product_forbidden_discount and line.product_id)
        for line in forbidden_discount_records:
            # if forbidden discount, we reset the value with the price unit of the product
            price = line.with_company(line.company_id)._get_display_price()
            line.price_unit = line.product_id._get_tax_included_unit_price(
                line.company_id,
                line.order_id.currency_id,
                line.order_id.date_order,
                'sale',
                fiscal_position=line.order_id.fiscal_position_id,
                product_price_unit=price,
                product_currency=line.currency_id,
            )
        super(SaleOrderLine, self - forbidden_discount_records)._compute_price_unit()

    def _compute_of_is_price_unit_readonly(self):
        """Compute the value of of_is_price_unit_readonly field

        Sales manager can modify the unit price of the sale order line.
        Sales responsible can modify the unit price of the sale order line only if he have the group
            `group_of_can_modify_sale_price_unit`.
        And other users can modifiy the unit price if they have group `group_of_can_modify_sale_price_unit` and product
        is not forbidden to discount.
        """
        for line in self:
            of_is_price_unit_readonly = True
            if self.env.user.has_group('sales_team.group_sale_manager'):
                of_is_price_unit_readonly = False
            elif self.env.user.user_has_groups(
                'of_sale.of_group_sale_responsible+of_sale_no_discount.group_of_can_modify_sale_price_unit'
            ):
                of_is_price_unit_readonly = False
            elif self.env.user.has_group('of_sale_no_discount.group_of_can_modify_sale_price_unit'):
                of_is_price_unit_readonly = line.of_product_forbidden_discount
            line.of_is_price_unit_readonly = of_is_price_unit_readonly
