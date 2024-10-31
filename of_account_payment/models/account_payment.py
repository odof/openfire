# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).


from odoo import api, fields, models


class AccountPayment(models.Model):
    _inherit = "account.payment"

    of_expected_deposit_date = fields.Date(string="Scheduled delivery date")
    of_payment_mode_id = fields.Many2one(comodel_name="of.payment.mode", string="Payment Mode")

    @api.model_create_multi
    def create(self, vals_list):
        payment_mode_obj = self.env["of.payment.mode"]
        for vals in vals_list:
            if "of_payment_mode_id" in vals and not vals.get("payment_method_line_id", False):
                payment_mode = payment_mode_obj.browse(vals.get("of_payment_mode_id"))
                vals["payment_method_line_id"] = payment_mode and payment_mode.payment_method_line_id.id

        return super().create(vals_list)
