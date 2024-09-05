# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models


class AccountMove(models.Model):
    _inherit = "account.move"

    def _compute_payments_widget_reconciled_info(self):
        vals = super()._compute_payments_widget_reconciled_info()
        config = ""
        for move in self:
            if move.invoice_payments_widget:
                if move.state == 'posted' and move.is_invoice(include_receipts=True):
                    reconciled_partials = move._get_all_reconciled_invoice_partials()
                    for i, reconciled_partial in enumerate(reconciled_partials):
                        counterpart_line = reconciled_partial['aml']
                        move.invoice_payments_widget['content'][i].update(
                            {
                                'payment_mode': counterpart_line.payment_id.payment_method_line_id.name,
                                'date_payment': counterpart_line.date.strftime("%d/%m/%Y"),
                            }
                        )
                        config = counterpart_line.payment_id.payment_method_line_id.config
        if not config:
            info_pattern = (
                self.env["ir.config_parameter"]
                .sudo()
                .get_param("of_account_invoice_report_payment_info.info_pattern", default="")
            )
        else:
            info_pattern = config
        Move = self.env["account.move"]
        for one in self:
            if not vals and not one.invoice_payments_widget:
                continue
            for payment_dict in one.invoice_payments_widget["content"]:
                move = Move.browse(payment_dict["move_id"])
                payment_dict["move_ref"] = move.ref
                payment_dict["extra_info"] = info_pattern.format(**payment_dict)
        return vals
