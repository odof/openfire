# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).


from odoo import fields, models


class AccountPayment(models.Model):
    _inherit = 'account.payment'

    of_expected_deposit_date = fields.Date(string="Scheduled delivery date")
    of_payment_mode_id = fields.Many2one(comodel_name='of.payment.mode', string="Payment Mode")
