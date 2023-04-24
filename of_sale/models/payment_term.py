# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


# TODO: Move me to `of_account` module when it will be migrated
class OfAccountPaymentTermLine(models.Model):
    _inherit = 'account.payment.term.line'

    of_option_date = fields.Selection(
        selection=[('invoice', "Invoice date"), ('previous', "Previous term")],
        string="Reference date",
        required=True,
        default='invoice',
    )


# End of TODO: Move me to `of_account` module when it will be migrated


class AccountPaymentTermLine(models.Model):
    _inherit = 'account.payment.term.line'

    of_option_date = fields.Selection(
        selection_add=[('order', "Order date"), ('previous',)], ondelete={'order': 'cascade'}
    )
