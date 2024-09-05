# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class AccountPaymentMethodLine(models.Model):
    _inherit = 'account.payment.method.line'

    @api.model
    def _get_default_of_display_config(self):
        config_parameter_obj = self.env['ir.config_parameter'].sudo()
        return config_parameter_obj.get_param('account_invoice_report_payment_info.info_pattern', default='')

    of_display_config = fields.Char(string="Paid Invoice Configuration", default=_get_default_of_display_config)
