# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, models


class SaleAdvancePaymentInv(models.TransientModel):
    _inherit = "sale.advance.payment.inv"

    @api.onchange("advance_payment_method")
    def _onchange_advance_payment_method(self):
        categ_deposit_id = self.env["ir.config_parameter"].sudo().get_param("of.sale.of_deposit_product_categ_id")
        categ_deposit_id = int(categ_deposit_id) if categ_deposit_id else False
        if len(self.sale_order_ids) > 1 or self.advance_payment_method == "delivered":
            return {}

        self = self.with_company(self.company_id)
        order = self.sale_order_ids
        nb_lines_deposit = len(
            order.mapped("order_line").filtered(lambda line: line.product_id.categ_id.id == categ_deposit_id)
        )
        nb_lines_deadlines = len(order.of_payment_schedule_ids)
        if nb_lines_deadlines < 2 or nb_lines_deposit >= nb_lines_deadlines - 1:
            return super()._onchange_advance_payment_method()
        if self.advance_payment_method == "fixed":
            deposit_amount = order.of_payment_schedule_ids[nb_lines_deposit].amount
            return {"value": {"fixed_amount": deposit_amount}}
        elif self.advance_payment_method == "percentage":
            deposit_amount = order.of_payment_schedule_ids[nb_lines_deposit].percent
            return {"value": {"amount": deposit_amount}}
        else:
            return {}
