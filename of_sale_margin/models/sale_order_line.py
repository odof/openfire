# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    of_seller_price = fields.Float(
        string="Purchase price",
        compute='_compute_of_seller_price',
        store=True,
        digits='Product Price',
        readonly=False,
        precompute=True,
    )

    @api.depends('product_id', 'company_id', 'currency_id', 'product_uom')
    def _compute_purchase_price(self):
        """Override to use the theoretical cost instead of the standard cost price when the cost method is not set to
        'standard'
        """
        for line in self:
            if not line.product_id:
                line.purchase_price = 0.0
                continue
            line = line.with_company(line.company_id)
            product_cost = line.product_id.get_cost()
            line.purchase_price = line._convert_price(product_cost, line.product_id.uom_id)

    @api.depends('product_id', 'company_id', 'currency_id', 'product_uom')
    def _compute_of_seller_price(self):
        for line in self:
            if line.product_id:
                line.of_seller_price = line._of_convert_price(line.product_id.of_seller_price, line.product_id.uom_id)

    def _of_convert_price(self, seller_price, from_uom):
        """
        Convert the seller price from the product's currency to the order's currency
        Based on `_convert_price` from `sale_margin/models/sale_order_line.py`
        """
        self.ensure_one()
        if not seller_price:
            return 0.0
        from_currency = self.product_id.cost_currency_id
        to_cur = self.currency_id or self.order_id.currency_id
        to_uom = self.product_uom
        if to_uom and to_uom != from_uom:
            seller_price = from_uom._compute_price(
                seller_price,
                to_uom,
            )
        return (
            from_currency._convert(
                from_amount=seller_price,
                to_currency=to_cur,
                company=self.company_id or self.env.company,
                date=self.order_id.date_order or fields.Date.today(),
                round=False,
            )
            if to_cur and seller_price
            else seller_price
        )
        # The pricelist may not have been set, therefore no conversion
        # is needed because we don't know the target currency..

    @api.model
    def read_group(self, domain, fields, groupby, offset=0, limit=None, orderby=False, lazy=True):
        """Override to change the way the margin percentage is displayed on pivot views.
        The default behavior displays the margin as a float <= 1.0, which is not very user-friendly.
        This method displays the margin as a percentage instead.
        """
        fname = 'margin_percent'
        field = self._fields.get(fname)
        func = field and field.group_operator  # default is `sum`
        if f'{fname}:{func}' in fields:
            for depends_field in ('margin', 'price_subtotal'):
                if f'{depends_field}:{func}' not in fields:
                    fields.append(f'{depends_field}:{func}')

        res = super().read_group(domain, fields, groupby, offset=offset, limit=limit, orderby=orderby, lazy=lazy)

        if f'{fname}:{func}' in fields:
            for line in res:
                if (
                    'margin' in line
                    and line['margin'] is not None
                    and 'price_subtotal' in line
                    and line['price_subtotal']
                ):
                    line['margin_percent'] = round(100.0 * line['margin'] / line['price_subtotal'], 2)
                else:
                    line['margin_percent'] = 0.0
        return res
