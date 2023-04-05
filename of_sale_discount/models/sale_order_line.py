# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import _, api, fields, models
from odoo.exceptions import UserError


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    discount = fields.Float(compute='_compute_discount')
    of_discount_formula = fields.Char(
        string="Discount (%)",
        compute='_compute_of_discount_formula',
        store=True,
        readonly=False,
        precompute=True,
        help="Discount or amount of discounts.\nEg. \"40 + 10.5\" equals \"46.3\"",
    )

    @api.depends('product_id', 'product_uom', 'product_uom_qty', 'of_discount_formula')
    def _compute_discount(self):
        super()._compute_discount()
        for line in self:
            price_percent = 100.0
            if line.of_discount_formula:
                try:
                    for discount in map(float, line.of_discount_formula.replace(',', '.').split('+')):
                        price_percent *= (100 - discount) / 100.0
                except Exception as e:
                    raise UserError(_("Invalid discount formula:\n%s") % line.of_discount_formula) from e
            line.discount = 100.0 - price_percent

    @api.depends('product_id', 'product_uom', 'product_uom_qty', 'price_unit', 'pricelist_item_id')
    def _compute_of_discount_formula(self):
        for line in self:
            if (
                not (
                    line.product_id
                    and line.order_id.pricelist_id
                    and line.order_id.pricelist_id.discount_policy == 'without_discount'
                )
                or line.display_type
            ):
                line.of_discount_formula = False
                continue

            line.of_discount_formula = str(line.discount) if line.discount else False
            if line.pricelist_item_id.compute_price == 'percentage':
                line.of_discount_formula = line.pricelist_item_id.of_percent_price_formula

    def _prepare_invoice_line(self, **optional_values):
        values = super()._prepare_invoice_line(**optional_values)
        values['of_discount_formula'] = self.of_discount_formula
        return values

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('of_discount_formula') and vals.get('discount'):
                vals['of_discount_formula'] = f"{vals['discount']}"
        return super().create(vals)

    def write(self, vals):
        if not vals.get('of_discount_formula') and vals.get('discount'):
            vals['of_discount_formula'] = f"{vals['discount']}"
        return super().write(vals)
