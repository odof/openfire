# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).


from odoo import _, api, fields, models
from odoo.exceptions import UserError


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    discount = fields.Float(  # like sale.order.line => store=True, readonly=False, precompute=True
        string="Discount (%)", compute='_of_compute_discount', store=True, readonly=False, precompute=True
    )
    of_discount_formula = fields.Char(
        string="Discount (%)", help="Discount or amount of discounts.\nEg. \"40 + 10.5\" equals \"46.3\""
    )

    @api.depends('of_discount_formula')
    def _of_compute_discount(self):
        for line in self:
            price_percent = 100.0
            if line.of_discount_formula:
                try:
                    for discount in map(float, line.of_discount_formula.replace(',', '.').split('+')):
                        price_percent *= (100 - discount) / 100.0
                except Exception as e:
                    raise UserError(_("Invalid discount formula:\n%s") % line.of_discount_formula) from e
            line.discount = 100.0 - price_percent

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('of_discount_formula') and vals.get('discount'):
                vals['of_discount_formula'] = f"{vals['discount']}"
        return super().create(vals_list)

    def write(self, vals):
        if not vals.get('of_discount_formula') and vals.get('discount'):
            vals['of_discount_formula'] = f"{vals['discount']}"
        return super().write(vals)

    def _get_fields_sync_mapping(self):
        res = super()._get_fields_sync_mapping()
        res['of_discount_formula'] = 'of_discount_formula'
        return res
