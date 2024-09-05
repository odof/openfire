# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class AccountPaymentMethodLine(models.Model):
    _inherit = 'account.payment.method.line'

    def _get_default_config(self):
        return (
            self.env["ir.config_parameter"]
            .sudo()
            .get_param("of_account_invoice_report_payment_info.info_pattern", default="")
        )

    config = fields.Char(default=_get_default_config)
