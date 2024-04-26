# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, models


class AccountPayment(models.Model):
    _inherit = 'account.payment'

    @api.model
    def _prepare_mutation_values(self, **args):
        mutation = {}

        if name := args.get('name'):
            mutation['name'] = name

        if amount_total := args.get('amount_total'):
            mutation['amount_total'] = amount_total

        if amount_residual := args.get('amount_residual'):
            mutation['amount_residual'] = amount_residual

        if payment_state := args.get('payment_state'):
            mutation['payment_state'] = payment_state

        if date := args.get('date'):
            mutation['date'] = date

        return mutation
