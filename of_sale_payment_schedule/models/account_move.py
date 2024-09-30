# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models


class AccountMove(models.Model):
    _inherit = "account.move"

    # TODO: Uncomment me and continue the migration when `of_account` module is migrated
    # def action_post(self):
    #     result = super().action_post()
    #     self._update_payment_schedule()
    #     return result

    # def _update_payment_schedule(self):
    #     """Update the payment schedule of the sale orders linked to the invoice"""
    #     of_deposit_product_categ_id = (
    #         self.env['ir.config_parameter'].sudo().get_param('of.sale.of_deposit_product_categ_id')
    #     )
    #     lines = self.mapped('invoice_line_ids').filtered(
    #         lambda line: line.product_id.categ_id.id != of_deposit_product_categ_id
    #     )
    #     orders = lines.mapped('sale_line_ids').mapped('order_id')
    #     orders.of_update_payment_schedule_dates()
    # End of TODO: Uncomment me and continue the migration when `of_account` module is migrated
