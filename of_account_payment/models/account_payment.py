# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).


from odoo import fields, models


class AccountPayment(models.Model):
    _inherit = 'account.payment'

    of_expected_deposit_date = fields.Date(string="Scheduled delivery date")
