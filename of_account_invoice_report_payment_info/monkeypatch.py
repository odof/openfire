# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models
from odoo.tools.misc import format_amount, format_date

from odoo.addons.account_invoice_report_payment_info.models.account_invoice import AccountMove

# Save the original methods
_compute_payments_widget_reconciled_info_original = AccountMove._compute_payments_widget_reconciled_info


class OFAccountInvoiceReportPaymentInfo(models.AbstractModel):
    """When you use monkey patching, the code is executed when the module
    is in the addons_path of the Odoo server, even is the module is not
    installed ! In order to avoid the side-effects it can create,
    we create an AbstractModel inside the module and we test the
    availability of this Model in the code of the monkey patching below.
    """

    _name = 'of.account.invoice.report.payment.info.installed'
    _description = "This model is used to test if the module is installed and avoid monkey patching side-effects."


def _compute_payments_widget_reconciled_info(self):
    if self.env.get('of.account.invoice.report.payment.info.installed') is None:
        return _compute_payments_widget_reconciled_info_original(self)

    res = super(AccountMove, self)._compute_payments_widget_reconciled_info()
    currency_obj = self.env['res.currency']
    move_obj = self.env['account.move']
    payment_obj = self.env['account.payment']
    for one in self:
        if not res and not one.invoice_payments_widget:
            continue
        for payment_dict in one.invoice_payments_widget['content']:
            currency = currency_obj.browse(payment_dict['currency_id'])
            move = move_obj.browse(payment_dict['move_id'])
            payment = payment_obj.browse(payment_dict['account_payment_id'])

            payment_dict['move_ref'] = move.ref
            payment_dict['payment_amount'] = format_amount(self.env, payment_dict['amount'], currency)
            payment_dict['date'] = format_date(self.env, payment_dict['date'])
            payment_dict['payment_mode'] = payment.of_payment_mode_id.shortname
            payment_dict['payment_reference'] = payment.payment_reference
            payment_dict['payment_method_id'] = payment.payment_method_line_id.id
            payment_dict['extra_info'] = payment.payment_method_line_id.of_display_config.format(**payment_dict)
    return res


# Replace the original methods with the new ones
AccountMove._compute_payments_widget_reconciled_info = _compute_payments_widget_reconciled_info
