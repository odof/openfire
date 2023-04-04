# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    of_product_forbidden_discount = fields.Boolean(  # TODO: move me to of_sale module when it will be migrated to v16
        string="Discount not allowed for this product", readonly=True
    )

    of_price_management_variation = fields.Float(string="Unit amount of price change related to price management")
    of_unit_price_variation = fields.Float(string="Unit amount of the price variation")

    def of_get_price_unit(self):  # TODO: move me to of_sale module when it will be migrated to v16
        """Return the price unit of the line, taking into account the price management"""
        self.ensure_one()
        product = self.product_id.with_context(
            lang=self.order_id.partner_id.lang,
            partner=self.order_id.partner_id.id,
            quantity=self.product_uom_qty,
            date=self.order_id.date_order,
            pricelist=self.order_id.pricelist_id.id,
            uom=self.product_uom.id,
            fiscal_position=self.env.context.get('fiscal_position'),
        )
        return self.env['account.tax']._fix_tax_included_price_company(
            self._get_display_price(), product.taxes_id, self.tax_id, self.company_id
        )
